"""email-test-harness — a CLI for verifying that the hotels-data email pipeline
correctly sends a test message to a given recipient address.

The harness does NOT modify the hotels-data project. It uses the public REST
API to create a test hotel and trigger the reminder flow, then polls the
emails_sending.email_queue table for the outcome.

See spec.md for the full design and acceptance criteria.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Iterator, Optional, Tuple

import httpx
import psycopg2


DEFAULT_API_BASE = "http://localhost:8082/api/v1/hotelsdata"
DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:54320/emails_sending"
DEFAULT_TIMEOUT_SEC = 30.0
DEFAULT_POLL_SLEEP_SEC = 1.0


@dataclass
class Report:
    hotel_id: str
    email: str
    queue_id: Optional[int]
    queue_status: Optional[str]
    failure_reason: str
    attempts: int
    elapsed_sec: float


# ---------- pure helpers ----------


def extract_hotel_id(body: bytes) -> Optional[str]:
    if not body:
        return None
    try:
        return json.loads(body).get("id")
    except (json.JSONDecodeError, AttributeError):
        return None


def should_retry(status: str) -> bool:
    return status in ("PENDING", "PROCESSING")


def format_report(r: Report) -> str:
    return json.dumps(asdict(r), indent=2)


# ---------- I/O helpers ----------


@contextmanager
def open_http(api_base: str) -> Iterator[httpx.Client]:
    client = httpx.Client(timeout=10.0)
    try:
        yield client
    finally:
        client.close()


@contextmanager
def open_db(db_url: str) -> Iterator[psycopg2.extensions.connection]:
    conn = psycopg2.connect(db_url)
    try:
        yield conn
    finally:
        conn.close()


def create_hotel(client: httpx.Client, api_base: str, email: str) -> Optional[str]:
    hotel_id = f"email-test-{uuid.uuid4().hex[:8]}"
    url = f"{api_base}/api/hotels/add-test"
    response = client.post(
        url,
        json={
            "hotelId": hotel_id,
            "name": "Test Email Hotel",
            "countryCode": "US",
            "emails": email,
            "niches": [],
            "groups": [],
        },
    )
    if response.status_code >= 400:
        print(
            f"ERROR: POST {url} returned {response.status_code}: {response.text}",
            file=sys.stderr,
        )
        return None
    return extract_hotel_id(response.content)


def trigger_reminder(client: httpx.Client, api_base: str, hotel_id: str) -> bool:
    url = f"{api_base}/api/hotels/{hotel_id}/force-remind"
    response = client.put(url)
    if response.status_code != 200:
        print(
            f"ERROR: PUT {url} returned {response.status_code}: {response.text}",
            file=sys.stderr,
        )
        return False
    return True


def check_queue_status(
    conn, email: str
) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, status, COALESCE(failure_reason, ''), retry_count, attempts "
            "FROM email_queue WHERE hotel_email = %s ORDER BY id DESC",
            (email,),
        )
        rows = cur.fetchall()
    if not rows:
        return (None, None, None, None)
    qid, status, reason, retry_count, attempts = rows[0]
    return (status, reason, qid, attempts)


def poll_until_terminal(
    conn,
    email: str,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    sleep_sec: float = DEFAULT_POLL_SLEEP_SEC,
) -> Tuple[bool, str, Optional[int], Optional[int], float]:
    start = time.monotonic()
    last_status: Optional[str] = None
    last_reason = ""
    last_qid: Optional[int] = None
    last_attempts: Optional[int] = 0
    while time.monotonic() - start < timeout_sec:
        status, reason, qid, attempts = check_queue_status(conn, email)
        last_status, last_reason, last_qid, last_attempts = status, reason, qid, attempts
        if status in ("SENT", "FAILED", "CANCELLED"):
            return (status == "SENT", reason, qid, attempts, time.monotonic() - start)
        if status is None:
            # No row yet — keep waiting but don't burn CPU
            time.sleep(sleep_sec)
            continue
        time.sleep(sleep_sec)
    return (False, last_reason or "timeout", last_qid, last_attempts, time.monotonic() - start)


# ---------- entry point ----------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="email-test-harness",
        description="Send a test email through the hotels-data pipeline.",
    )
    parser.add_argument("email", help="recipient address to send the test email to")
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"hotels-data API base URL (default {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help=f"JDBC url for emails_sending (default {DEFAULT_DB_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SEC,
        help=f"max wait for the email to leave PENDING (default {DEFAULT_TIMEOUT_SEC}s)",
    )
    parser.add_argument(
        "--hotel-id",
        help="reuse an existing hotel id instead of creating a new one",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan, do not call the API or DB",
    )
    return parser


def main(argv: list) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.dry_run:
        report = Report(
            hotel_id="dry-run",
            email=args.email,
            queue_id=None,
            queue_status="DRY_RUN",
            failure_reason="",
            attempts=0,
            elapsed_sec=0.0,
        )
        print(format_report(report))
        return 0

    try:
        with open_http(args.api_base) as client:
            if args.hotel_id:
                hotel_id = args.hotel_id
            else:
                hotel_id = create_hotel(client, args.api_base, args.email)
                if not hotel_id:
                    print("ERROR: failed to create hotel", file=sys.stderr)
                    return 2

            if not trigger_reminder(client, args.api_base, hotel_id):
                print(
                    f"ERROR: failed to trigger reminder for {hotel_id}",
                    file=sys.stderr,
                )
                return 2

        with open_db(args.db_url) as conn:
            ok, reason, qid, attempts, elapsed = poll_until_terminal(
                conn,
                args.email,
                timeout_sec=args.timeout,
                sleep_sec=0.5,
            )

        report = Report(
            hotel_id=hotel_id,
            email=args.email,
            queue_id=qid,
            queue_status="SENT" if ok else "FAILED",
            failure_reason="" if ok else (reason or ""),
            attempts=attempts or 0,
            elapsed_sec=elapsed,
        )
        print(format_report(report))
        return 0 if ok else 1
    except ConnectionError as e:
        print(f"ERROR: connection failed: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
