# email-test-harness — tasks

Ordered by dependency. TDD-style: write the failing test first, then make it
green with the smallest possible change. After the harness is GREEN, each
task below also gets a corresponding GitHub issue.

| # | Task | Depends on | Test first (TDD RED) | Then implement (GREEN) | Acceptance |
|---|------|-----------|----------------------|------------------------|------------|
| 1 | Init project layout (`.specify/specs/email-test-harness/{spec,plan,tasks}.md`, `.specify/memory/constitution.md`, `src/`, `tests/`, `.github/workflows/ci.yml`, `requirements.txt`, `README.md`, `.gitignore`) | — | n/a | n/a | directories and stubs exist |
| 2 | `extract_hotel_id(bytes) -> Optional[str]` parses JSON `{id: ...}`; None on empty/garbage | 1 | `test_extract_hotel_id_from_addtest_response`, `test_extract_hotel_id_handles_empty_body` | one-line `json.loads + .get` with try/except | tests pass |
| 3 | `should_retry(status: str) -> bool` True for {PENDING, PROCESSING}, False otherwise | 1 | `test_should_retry_returns_true_for_pending_or_processing` | one-liner `in {"PENDING", "PROCESSING"}` | tests pass |
| 4 | `Report` dataclass + `format_report(r) -> str` (JSON dumps) | 1 | `test_build_report_serializes_to_json` | dataclass + `json.dumps(asdict(r), indent=2)` | test parses the output and checks keys |
| 5 | `create_hotel(client, api_base, email) -> str` — POSTs `/api/hotels/add-test` with `{hotelId, name, countryCode, emails, niches, groups}`, parses response for `id` | 2 | `test_create_hotel_posts_to_addtest_endpoint`, `test_create_hotel_returns_id_from_response_body` | httpx call, parse JSON via `extract_hotel_id` | tests pass |
| 6 | `trigger_reminder(client, api_base, hotel_id) -> bool` — PUTs `/api/hotels/{id}/force-remind`, True iff status 200 | 5 | `test_trigger_reminder_uses_force_remind_path`, `test_trigger_reminder_returns_false_on_400` | httpx call, check status | tests pass |
| 7 | `check_queue_status(conn, email) -> (status, reason, qid, attempts)` — SELECT latest row; return (None, None, None, None) if none | 4 | `test_check_queue_status_returns_status_for_latest_email`, `test_check_queue_status_returns_pending_when_only_pending`, `test_check_queue_status_returns_none_when_no_rows` | `cur.execute("SELECT ... ORDER BY id DESC")`, `cur.fetchall()`, unpack `rows[0]` | tests pass |
| 8 | `open_http(api_base) -> Iterator[httpx.Client]` (context manager) + `open_db(db_url) -> Iterator[psycopg2.connection]` | 5, 7 | indirect (via the tests that mock `open_http` / `open_db`) | use `@contextmanager` decorator + `yield` | tests pass |
| 9 | `poll_until_terminal(conn, email, timeout_sec, sleep_sec) -> (ok, reason, qid, attempts, elapsed)` — polls until terminal status or timeout | 3, 7 | `test_poll_until_terminal_stops_when_succeeded`, `test_poll_until_terminal_stops_when_failed` | `while time.monotonic()-start < timeout: ... sleep` | tests pass |
| 10 | `main(argv) -> int` CLI entry — argparse, --dry-run short-circuit, orchestrate open_http + create_hotel + trigger_reminder + open_db + poll_until_terminal, return 0/1/2 by exit-code table | 2, 3, 4, 5, 6, 7, 8, 9 | `test_main_returns_0_when_email_succeeds`, `test_main_returns_1_when_email_fails`, `test_main_returns_2_on_connection_error`, `test_cli_runs_and_prints_json` | argparse + the calls above + dict-to-JSON | tests pass |
| 11 | CI: `.github/workflows/ci.yml` — pytest on push/PR to main (Python 3.12) | 1-10 | n/a | write the workflow | green run on GitHub |
| 12 | README — usage, exit codes, examples, non-goals | 10 | n/a | n/a | links to spec/plan/tasks |
| 13 | Reset git history to comply with GitFlow: re-create `main` as the only branch, all commits reachable from `main` | 1-12 | n/a | `git checkout --orphan main main-files; git commit; git branch -D master` (or equivalent) | clean linear history on `main` |

## GitHub issues

After the harness is GREEN (tasks 1-10 complete), each numbered task above
gets a corresponding GitHub issue on the project's tracker, tagged
`enhancement` (or `task`), with the task description copied from this
table.
