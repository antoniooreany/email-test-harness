# email-test-harness

A small CLI for verifying that the **hotels-data** email pipeline correctly
sends a test message to a chosen recipient address. It exercises the public
REST API and reads the `emails_sending.email_queue` table — it does **not**
modify the hotels-data project tree in any way.

## What it does

Given a target email, the harness:

1. Creates a test hotel via `POST /api/v1/hotelsdata/api/hotels/add-test`
2. Triggers the reminder pipeline via `PUT /api/v1/hotelsdata/api/hotels/{id}/force-remind`
3. Polls `emails_sending.email_queue` until the email reaches a terminal state
4. Prints a JSON report describing what happened

Typical use: validate outbound quality against a service like
[https://www.mail-tester.com/](https://www.mail-tester.com/).

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
python src/email_harness.py <email> [OPTIONS]
```

Positional:
- `EMAIL` — recipient address to send the test email to (e.g. `test-xyz@srv1.mail-tester.com`)

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--api-base URL` | `http://localhost:8082/api/v1/hotelsdata` | hotels-data base URL |
| `--db-url URL` | `postgresql://postgres:postgres@localhost:54320/emails_sending` | emails_sending JDBC url |
| `--timeout SECONDS` | `30` | max wait for the email to leave PENDING |
| `--hotel-id ID` | — | reuse an existing hotel id instead of creating a new one |
| `--dry-run` | — | print the plan, do not call the API or DB |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | email reached `SENT` before the timeout |
| 1 | email reached `FAILED` with a non-empty `failure_reason` |
| 2 | usage / connection error (no hotel, hotel config missing, db unreachable) |

## Example (dry-run)

```bash
$ python src/email_harness.py test-abc@srv1.mail-tester.com --dry-run
{
  "hotel_id": "dry-run",
  "email": "test-abc@srv1.mail-tester.com",
  "queue_id": null,
  "queue_status": "DRY_RUN",
  "failure_reason": "",
  "attempts": 0,
  "elapsed_sec": 0.0
}
```

## Example (real run against local dev)

```bash
$ python src/email_harness.py test-abc@srv1.mail-tester.com
{
  "hotel_id": "email-test-a1b2c3d4",
  "email": "test-abc@srv1.mail-tester.com",
  "queue_id": 42,
  "queue_status": "SENT",
  "failure_reason": "",
  "attempts": 1,
  "elapsed_sec": 3.27
}
```

## Run the tests

```bash
pytest tests/
```

## What this project does NOT do

- Modify the hotels-data source tree
- Install Kafka / Mongo / Postgres locally
- Bypass the hotels-data email pipeline
- Authenticate with the hotels-data API (local dev runs without auth)

See `spec.md` for the full design.
