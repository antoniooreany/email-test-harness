# email-test-harness — implementation plan

## Overview

A small Python CLI that:
1. Creates (or reuses) a test hotel via the hotels-data public REST API.
2. Triggers a single reminder cycle.
3. Polls the `emails_sending.email_queue` table until the row reaches a
   terminal state, then prints a JSON report and exits with a meaningful code.

The whole project is one Python file + one test file + config. It does not
modify the hotels-data source tree.

## Module / file layout

```
email-test-harness/
├── .specify/
│   └── specs/email-test-harness/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
├── .specify/memory/
│   └── constitution.md
├── src/
│   └── email_harness.py        # the only production module
├── tests/
│   └── test_email_harness.py   # all tests, no separate test files needed
├── .github/workflows/
│   └── ci.yml                 # GitHub Actions: pytest on push/PR
├── requirements.txt
├── README.md
├── .gitignore
└── spec.md → moved to .specify/specs/email-test-harness/spec.md
```

## Module: `src/email_harness.py`

Exports the public API used by tests and the CLI.

| Symbol | Kind | Notes |
|--------|------|-------|
| `Report` | dataclass | fields: hotel_id, email, queue_id, queue_status, failure_reason, attempts, elapsed_sec |
| `extract_hotel_id(body: bytes) -> Optional[str]` | function | parses JSON, returns "id" field or None on failure |
| `should_retry(status: str) -> bool` | function | True iff status in {PENDING, PROCESSING} |
| `format_report(r: Report) -> str` | function | `json.dumps(asdict(r), indent=2)` |
| `open_http(api_base: str) -> Iterator[httpx.Client]` | context manager | yields a configured `httpx.Client` |
| `open_db(db_url: str) -> Iterator[psycopg2.connection]` | context manager | yields a configured psycopg2 connection |
| `create_hotel(client, api_base, email) -> Optional[str]` | function | POSTs to `/api/hotels/add-test`, returns the new hotel id (UUID) |
| `trigger_reminder(client, api_base, hotel_id) -> bool` | function | PUTs to `/api/hotels/{id}/force-remind`, True iff 200 |
| `check_queue_status(conn, email) -> tuple` | function | SELECTs the latest row from `email_queue` for the given email; returns (status, reason, queue_id, attempts) or (None, None, None, None) |
| `poll_until_terminal(conn, email, timeout_sec, sleep_sec) -> tuple` | function | polls `check_queue_status` until status is SENT/FAILED/CANCELLED or timeout; returns (ok, reason, qid, attempts, elapsed_sec) |
| `build_arg_parser() -> argparse.ArgumentParser` | function | builds the CLI parser |
| `main(argv) -> int` | function | CLI entry, returns 0/1/2 exit code |

## SQL contract (read-only)

| Query | Used by | Returns |
|-------|---------|---------|
| `SELECT id, status, COALESCE(failure_reason,''), retry_count, attempts FROM email_queue WHERE hotel_email = %s ORDER BY id DESC` | `check_queue_status` | (id, status, reason, retry_count, attempts) for the newest row, or no rows |

## REST contract

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `{apiBase}/api/hotels/add-test` | `{hotelId, name, countryCode, emails, niches, groups}` (JSON) | any 2xx, body parsed for `id` field |
| PUT | `{apiBase}/api/hotels/{id}/force-remind` | — | 200 with `{reminded: bool, message: str}` |

## Dependencies

- `httpx >= 0.27` — HTTP client
- `psycopg2-binary >= 2.9` — PostgreSQL driver
- `pytest >= 7.0` — dev / test only

## CI

GitHub Actions workflow at `.github/workflows/ci.yml`:
- Trigger: push and pull_request to main
- Run: `pip install -r requirements.txt && pytest -v`
- Python version: 3.12

## Test strategy

17 unit tests in `tests/test_email_harness.py`:
- Pure-function tests (no I/O): extract_hotel_id, should_retry, format_report
- Mocked I/O tests: create_hotel, trigger_reminder, check_queue_status, poll_until_terminal
- Main-loop tests: main with mocked dependencies
- CLI smoke test: subprocess run with --dry-run, validates stdout JSON keys

All tests use a `MagicMock` helper `_cm_mock(...)` that builds a real
DB-API-style context manager (cursor is its own `__enter__`).

## Out of plan

- Building or running Kafka / Mongo / Postgres locally
- Modifying the hotels-data project tree
- Sending email outside the hotels-data pipeline
- Authentication
