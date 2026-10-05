# email-test-harness — spec

## Goal

Provide a CLI test harness that validates the **hotels-data** email pipeline
sends a message to a chosen recipient address (e.g. `test-xxx@srv1.mail-tester.com`)
correctly. The harness must run end-to-end against a real (or real-looking)
local instance of hotels-data without modifying the hotels-data source tree.

## Scope

In scope:
- Create a test hotel via `POST /api/v1/hotelsdata/api/hotels/add-test`
- Set its email via DB or API
- Trigger the reminder pipeline via `PUT /api/v1/hotelsdata/api/hotels/{id}/force-remind`
- Poll the `emails_sending.email_queue` table until the email reaches a
  terminal state (`SENT` or `FAILED` with a non-empty `failure_reason`)
- Print a structured JSON report describing what happened
- Exit 0 on success, 1 on email failure, 2 on usage / connection error

Out of scope:
- Modifying the hotels-data source tree
- Installing Kafka / Mongo / Postgres locally
- Authenticating with the hotels-data API (local dev runs without auth)

## Inputs

Positional:
- `EMAIL` — recipient address (e.g. `test-abc@srv1.mail-tester.com`)

Options:
- `--api-base URL` (default `http://localhost:8082/api/v1/hotelsdata`)
- `--db-url URL` (default `postgresql://postgres:postgres@localhost:54320/emails_sending`)
- `--timeout SECONDS` (default 30)
- `--hotel-id ID` (reuse existing hotel id instead of creating a new one)
- `--dry-run` (print the plan, do not call the API or DB)

## Outputs

JSON object printed to stdout with at minimum:
- `hotel_id` (string)
- `email` (string)
- `queue_id` (int or null)
- `queue_status` (string — `SENT` / `FAILED` / `DRY_RUN` / etc.)
- `failure_reason` (string)
- `attempts` (int)
- `elapsed_sec` (float)

## Acceptance criteria

1. Exit 0 when the email reaches `SENT` before the timeout.
2. Exit 1 when the email reaches `FAILED` with a non-empty `failure_reason`.
3. Exit 2 on usage / connection errors (no hotel, hotel config missing, db unreachable).
4. JSON output is parseable by `json.loads()` and contains all six required keys.
5. Polling times out after `--timeout` seconds (default 30).
6. Default DB connection: `postgresql://postgres:postgres@localhost:54320/emails_sending`.
7. Default API base: `http://localhost:8082/api/v1/hotelsdata`.

## Out of scope (re-stated)

This is a test harness for an existing pipeline. It does not:
- Send email from a non-hotels-data address
- Authenticate with the hotels-data API
- Clean up created test hotels (they're left for manual inspection)
- Add new hotels-data features or test data
