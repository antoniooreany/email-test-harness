"""Tests for email-test-harness. RED phase of TDD — these tests should fail
until the implementation in src/email_harness.py exists."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

# Make src/ importable
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

# Will be imported after implementation exists; stub the module so the
# import does not blow up while these tests are still red.
import importlib

try:
    eh = importlib.import_module("email_harness")
except ModuleNotFoundError:
    eh = None


# ---------- helpers ----------


def _cm_mock(*, fetchall_return=None, fetchall_side_effect=None):
    """Build a MagicMock that behaves like a real DB-API cursor:
    supports `with cm as c:` (the cursor is its own context manager) and
    exposes .execute() and .fetchall()."""
    cur = MagicMock()
    if fetchall_side_effect is not None:
        cur.fetchall.side_effect = fetchall_side_effect
    if fetchall_return is not None:
        cur.fetchall.return_value = fetchall_return
    cur.__enter__.return_value = cur
    cur.__exit__.return_value = False
    return cur


# ---------- pure-function tests (no I/O) ----------


def test_extract_hotel_id_from_addtest_response():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    body = json.dumps({"id": "hotel-abc-123", "name": "Test"}).encode()
    assert eh.extract_hotel_id(body) == "hotel-abc-123"


def test_extract_hotel_id_handles_empty_body():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    assert eh.extract_hotel_id(b"") is None
    assert eh.extract_hotel_id(b"not-json") is None


def test_should_retry_returns_true_for_pending_or_processing():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    assert eh.should_retry("PENDING") is True
    assert eh.should_retry("PROCESSING") is True
    assert eh.should_retry("SENT") is False
    assert eh.should_retry("FAILED") is False
    assert eh.should_retry("CANCELLED") is False


def test_build_report_serializes_to_json():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    report = eh.Report(
        hotel_id="hotel-1",
        email="x@y",
        queue_id=42,
        queue_status="SENT",
        failure_reason="",
        attempts=1,
        elapsed_sec=2.5,
    )
    s = eh.format_report(report)
    parsed = json.loads(s)
    assert parsed["hotel_id"] == "hotel-1"
    assert parsed["queue_status"] == "SENT"
    assert parsed["attempts"] == 1


# ---------- mocked-I/O tests ----------


def test_create_hotel_posts_to_addtest_endpoint():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    response = MagicMock(status_code=200, content=b"")
    client = MagicMock()
    client.post.return_value = response
    hotel_id = eh.create_hotel(client, "http://api", "x@y.com")
    client.post.assert_called_once()
    call = client.post.call_args
    assert call.args[0] == "http://api/api/hotels/add-test"
    payload = call.kwargs["json"]
    assert payload["emails"] == "x@y.com"
    assert "hotelId" in payload and payload["hotelId"].startswith("email-test-")


def test_create_hotel_returns_id_from_response_body():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    response = MagicMock(status_code=200, content=b'{"id":"hotel-xyz"}')
    client = MagicMock()
    client.post.return_value = response
    hotel_id = eh.create_hotel(client, "http://api", "x@y.com")
    assert hotel_id == "hotel-xyz"


def test_trigger_reminder_uses_force_remind_path():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    response = MagicMock(
        status_code=200,
        content=b'{"reminded":true,"message":"Hotel reminded successfully"}',
    )
    client = MagicMock()
    client.put.return_value = response
    reminded = eh.trigger_reminder(client, "http://api", "hotel-abc")
    assert reminded is True
    client.put.assert_called_once()
    assert client.put.call_args.args[0] == "http://api/api/hotels/hotel-abc/force-remind"


def test_trigger_reminder_returns_false_on_400():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    response = MagicMock(status_code=400, content=b'{"reminded":false,"message":"x"}')
    client = MagicMock()
    client.put.return_value = response
    assert eh.trigger_reminder(client, "http://api", "hotel-abc") is False


def test_check_queue_status_returns_status_for_latest_email():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    rows = [
        (2, "SENT", "", 0, 2),
        (1, "PENDING", "", 0, 1),
    ]
    conn = MagicMock()
    conn.cursor.return_value = _cm_mock(fetchall_return=rows)
    status, reason, qid, attempts = eh.check_queue_status(conn, "x@y.com")
    assert status == "SENT"
    assert reason == ""
    assert qid == 2
    assert attempts == 2


def test_check_queue_status_returns_pending_when_only_pending():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    conn = MagicMock()
    conn.cursor.return_value = _cm_mock(fetchall_return=[(1, "PENDING", "", 0, 1)])
    status, reason, qid, attempts = eh.check_queue_status(conn, "x@y.com")
    assert status == "PENDING"
    assert qid == 1


def test_check_queue_status_returns_none_when_no_rows():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    conn = MagicMock()
    conn.cursor.return_value = _cm_mock(fetchall_return=[])
    assert eh.check_queue_status(conn, "x@y.com") == (None, None, None, None)


def test_main_returns_0_when_email_succeeds():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    with patch.object(eh, "create_hotel", return_value="hotel-1"), \
         patch.object(eh, "trigger_reminder", return_value=True), \
         patch.object(eh, "poll_until_terminal", return_value=(True, "", 1, 1, 0.5)), \
         patch.object(eh, "open_http", return_value=MagicMock()), \
         patch.object(eh, "open_db", return_value=MagicMock()):
        rc = eh.main(["x@y.com"])
    assert rc == 0


def test_main_returns_1_when_email_fails():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    with patch.object(eh, "create_hotel", return_value="hotel-1"), \
         patch.object(eh, "trigger_reminder", return_value=True), \
         patch.object(eh, "poll_until_terminal", return_value=(False, "smtp fail", 1, 3, 0.7)), \
         patch.object(eh, "open_http", return_value=MagicMock()), \
         patch.object(eh, "open_db", return_value=MagicMock()):
        rc = eh.main(["x@y.com"])
    assert rc == 1


def test_main_returns_2_on_connection_error():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    with patch.object(eh, "open_http", side_effect=ConnectionError("no api")):
        rc = eh.main(["x@y.com"])
    assert rc == 2


def test_poll_until_terminal_stops_when_succeeded():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    conn = MagicMock()
    conn.cursor.return_value = _cm_mock(
        fetchall_side_effect=[
            [(1, "PENDING", "", 0, 1)],
            [(2, "SENT", "", 0, 2)],
        ]
    )
    ok, reason, qid, attempts, elapsed = eh.poll_until_terminal(
        conn, "x@y.com", timeout_sec=2.0, sleep_sec=0.01
    )
    assert ok is True
    assert qid == 2


def test_poll_until_terminal_stops_when_failed():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    conn = MagicMock()
    conn.cursor.return_value = _cm_mock(
        fetchall_side_effect=[
            [(1, "PENDING", "", 0, 1)],
            [(3, "FAILED", "smtp timeout", 0, 3)],
        ]
    )
    ok, reason, qid, attempts, elapsed = eh.poll_until_terminal(
        conn, "x@y.com", timeout_sec=2.0, sleep_sec=0.01
    )
    assert ok is False
    assert reason == "smtp timeout"
    assert qid == 3


# ---------- CLI smoke test via subprocess ----------


def test_cli_runs_and_prints_json():
    """End-to-end smoke: run the script as a subprocess, capture stdout,
    assert it produced a JSON object with the expected top-level keys.
    This is a coarse check; finer-grained behaviour is covered above."""
    script = Path(__file__).resolve().parent.parent / "src" / "email_harness.py"
    if not script.exists():
        pytest.skip("email_harness.py not yet implemented")
    # --dry-run avoids touching the API; expect exit code 0 and a JSON payload.
    result = subprocess.run(
        [sys.executable, str(script), "x@y.com", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    for key in ("hotel_id", "email", "queue_status", "attempts"):
        assert key in parsed, f"missing key {key!r} in {parsed!r}"


# ---------- orchestration tests ----------


def test_check_service_up_returns_true_for_2xx():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    fake_client = MagicMock()
    fake_client.get.return_value = MagicMock(status_code=200)
    with patch("httpx.Client", return_value=fake_client):
        with patch("httpx.Client.__enter__", return_value=fake_client), \
             patch("httpx.Client.__exit__", return_value=False):
            assert eh.check_service_up("http://api", timeout_sec=1.0) is True


def test_check_service_up_returns_false_for_5xx():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    fake_client = MagicMock()
    fake_client.get.return_value = MagicMock(status_code=500)
    with patch("httpx.Client", return_value=fake_client), \
         patch("httpx.Client.__enter__", return_value=fake_client), \
         patch("httpx.Client.__exit__", return_value=False):
        assert eh.check_service_up("http://api", timeout_sec=1.0) is False


def test_check_service_up_returns_false_on_connection_error():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    fake_client = MagicMock()
    fake_client.get.side_effect = eh.httpx.ConnectError("nope")
    with patch("httpx.Client", return_value=fake_client), \
         patch("httpx.Client.__enter__", return_value=fake_client), \
         patch("httpx.Client.__exit__", return_value=False):
        assert eh.check_service_up("http://api", timeout_sec=1.0) is False


def test_wait_for_service_ready_returns_true_when_already_up():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    with patch.object(eh, "check_service_up", return_value=True):
        assert (
            eh.wait_for_service_ready(
                "http://api", timeout_sec=2.0, sleep_sec=0.01
            )
            is True
        )


def test_wait_for_service_ready_returns_false_on_timeout():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    with patch.object(eh, "check_service_up", return_value=False), \
         patch.object(eh.time, "sleep"):
        assert (
            eh.wait_for_service_ready(
                "http://api", timeout_sec=0.1, sleep_sec=0.01
            )
            is False
        )


def test_start_hotel_data_if_needed_skips_when_already_up():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    with patch.object(eh, "check_service_up", return_value=True), \
         patch.object(eh._subprocess, "run") as mock_run:
        result = eh.start_hotel_data_if_needed(
            "/hotels-data", "http://api", timeout_sec=30
        )
    assert result is True
    mock_run.assert_not_called()


def test_start_hotel_data_if_needed_runs_pwsh_when_not_running():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    fake_proc = MagicMock(returncode=0)
    with patch.object(eh, "check_service_up", side_effect=[False, True]), \
         patch.object(eh._subprocess, "run", return_value=fake_proc) as mock_run, \
         patch.object(eh.time, "sleep"):
        result = eh.start_hotel_data_if_needed(
            "/hotels-data", "http://api", timeout_sec=30
        )
    assert result is True
    mock_run.assert_called_once()
    # verify it invoked pwsh with the ps1 script
    args = mock_run.call_args[0][0]
    assert any("run-local.ps1" in str(a) for a in args), f"expected run-local.ps1 in {args}"


def test_orchestrate_services_returns_true_when_all_already_up():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    with patch.object(eh, "check_service_up", return_value=True):
        with patch("email_harness.open_db") as mock_open_db:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            mock_open_db.return_value.__enter__.return_value = mock_conn
            assert (
                eh.orchestrate_services(
                    "/hotels-data", "http://api", "postgres://x", start_timeout_sec=30
                )
                is True
            )


def test_orchestrate_services_starts_hotel_data_when_api_down():
    if eh is None:
        pytest.skip("email_harness not implemented yet")
    fake_proc = MagicMock(returncode=0)
    with patch.object(eh, "check_service_up", side_effect=[False, True]), \
         patch.object(eh._subprocess, "run", return_value=fake_proc), \
         patch.object(eh.time, "sleep"), \
         patch("email_harness.open_db") as mock_open_db:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            mock_open_db.return_value.__enter__.return_value = mock_conn
            assert (
                eh.orchestrate_services(
                    "/hotels-data", "http://api", "postgres://x", start_timeout_sec=30
                )
                is True
            )
