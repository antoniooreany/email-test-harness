# email-test-harness

A CLI test harness for verifying that the hotels-data email pipeline correctly
sends messages to a target address. Used to validate outbound email quality
(e.g. against mail-tester.com) without touching the hotels-data project code.

## Goal

Given a target email address, the harness:

1. Creates a test hotel in hotels-data with that email via the public REST API
   (`POST /api/v1/hotelsdata/api/hotels/add-test`).
2. Triggers the hotel reminder pipeline via the public REST API
   (`PUT /api/v1/hotelsdata/api/hotels/{id}/force-remind`).
3. Polls the `emails_sending.email_queue` table until the email is
   `SENT` (or `FAILED` with a non-empty `failure_reason`).
4. Prints a structured report describing what happened.

## Non-goals

- This project does NOT modify the hotels-data source tree.
- It does NOT install Kafka, Mongo, Postgres, or any hotels-data dependency.
- It does NOT bypass the hotels-data email pipeline — it exercises the public
  REST surface and inspects the public database tables via read-only SQL.

## API contract (hotels-data v3.4.1)

| Method | Path | Body | Effect |
|--------|------|------|--------|
| POST | `/api/v1/hotelsdata/api/hotels/add-test` | `AddTestHotelRequest` JSON | creates a test hotel; returns 200/204 |
| PUT | `/api/v1/hotelsdata/api/hotels/{id}/force-remind` | – | triggers one reminder cycle; returns `{reminded: bool, message: str}` |

Both endpoints live behind the same Spring context that the harness does
NOT host; the harness only reaches them over HTTP. Auth is out of scope
for local development; the harness does not send credentials.

## SQL contract (read-only)

The harness reads from `emails_sending.email_queue`:

| Column | Type | Meaning |
|--------|------|---------|
| id | bigint | primary key |
| hotel_email | varchar | recipient |
| subject | varchar | subject line |
| status | varchar | `PENDING` / `PROCESSING` / `SENT` / `FAILED` / `CANCELLED` |
| failure_reason | varchar | populated on `FAILED` |
| retry_count | int | attempts so far |

## Acceptance criteria

- `email-test-harness send EMAIL` must:
  1. Exit 0 on a clean send (status becomes `SENT` before the timeout).
  2. Exit 1 if the email reaches `FAILED` with a non-empty `failure_reason`.
  3. Exit 2 on usage / connection errors (no hotel, hotel config missing, db unreachable).
  4. Print a JSON report on stdout with at minimum:
     `hotel_id`, `email`, `queue_id`, `queue_status`, `failure_reason`, `attempts`.
  5. Poll for at most 30 seconds (configurable via `--timeout`).
  6. Default DB connection: `postgresql://postgres:postgres@localhost:54320/emails_sending`.
  7. Default API base: `http://localhost:8082/api/v1/hotelsdata`.

## CLI

```text
email-test-harness send EMAIL [OPTIONS]

Arguments:
  EMAIL                     recipient address to send the test email to

Options:
  --api-base URL            hotels-data base URL (default http://localhost:8082/api/v1/hotelsdata)
  --db-url URL              JDBC url for emails_sending (default postgresql://postgres:postgres@localhost:54320/emails_sending)
  --timeout SECONDS         max wait for the email to leave PENDING (default 30)
  --hotel-id ID             reuse an existing hotel id instead of creating a new one
  --dry-run                 print the plan, do not call the API or DB
```

## Out of scope

- Sending email from a non-hotels-data address (the harness is a *test* for the
  hotels-data pipeline, not a generic email sender).
- Authenticating with the hotels-data API (local dev runs without auth).
- Cleaning up created test hotels (the harness leaves them for manual inspection).
