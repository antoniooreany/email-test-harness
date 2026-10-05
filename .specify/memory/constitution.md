# email-test-harness — constitution

The non-negotiable rules this project must follow.

## 1. SDD first, then TDD, then GitFlow, with CI/CD

- **SDD (Spec-Driven Development):** every change starts from a spec in
  `.specify/specs/email-test-harness/` (spec.md + plan.md + tasks.md). The
  spec is the source of truth for what we are building and why.
- **TDD (Test-Driven Development):** the failing test is written before the
  implementation that makes it pass. `git log -p` should show the test
  predating the production change in the same commit, or in the commit
  immediately before it.
- **GitFlow:** the only long-lived branch in this repository is `main`.
  All work is committed directly to `main` after the spec + test are
  green. Do not create long-lived feature branches.
- **CI/CD:** every push to `main` runs `pytest` in GitHub Actions. A
  failing pipeline blocks the merge.

## 2. The harness does NOT modify the hotels-data source tree

The whole point of this project is to test an existing pipeline without
touching it. Any change to the hotels-data repository, its Gradle build,
its CI, or its Docker config is out of scope. If the user asks for such a
change, route it back to the hotels-data repo (per the appropriate
Jira-ticket branch), not here.

## 3. One source file, one test file

`src/email_harness.py` is the only production module. `tests/test_email_harness.py`
is the only test module. Do not split into multiple files unless the test
file exceeds ~1000 lines or a new file has zero coupling to the rest.

## 4. Mocks must mirror the real protocol

- For HTTP: `httpx.Client(base_url=...)` is mocked with `MagicMock` whose
  `post` / `put` return a `MagicMock(status_code=..., content=...)` matching
  the real hotels-data response.
- For Postgres: the cursor mock is a `MagicMock` whose `__enter__` returns
  itself (helper `_cm_mock` in the test file) so `with conn.cursor() as cur:`
  behaves like a real psycopg2 cursor.

## 5. Single exit-code contract

| Code | Meaning |
|------|---------|
| 0 | email reached `SENT` before the timeout |
| 1 | email reached `FAILED` with a non-empty `failure_reason` |
| 2 | usage / connection error (no hotel, hotel config missing, db unreachable) |

Do not invent new exit codes. The dry-run path must return 0.

## 6. Out of scope

- Installing or running Kafka / Mongo / Postgres locally
- Authenticating with the hotels-data API
- Cleaning up created test hotels (the harness leaves them for manual
  inspection in the local dev environment)
- Sending email from a non-hotels-data address
- Adding new hotels-data features or test data
