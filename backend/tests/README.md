Run from `backend/` with Python 3.11:

```powershell
python -m pip install -r requirements-test.txt
python -m pytest tests/unit --cov=app --cov-report=xml
python -m pytest tests/integration
```

Integration tests require a running Docker daemon using Linux containers.
Every pytest run generates a self-contained HTML report at
`backend/reports/test-report.html` (when running from `backend/`). Open it in
your browser after the run, including failed runs. Use `--html=reports/name.html`
to keep separate reports rather than overwrite the default.

The workflow generates `unit-tests.html`, `integration-tests.html`, and an HTML
coverage report inside its `backend-test-reports` artifact. Download the artifact
from the workflow run and open the HTML files locally. Integration tests also run
if unit tests fail; either failure still blocks deployment. A run that fails before
pytest starts cannot generate a test report.

Testcontainers builds an isolated API image, starts it on a dynamically mapped
port, waits for HTTP readiness, and removes the container and image afterward.
DuckDB is embedded, so the real database lives inside the API container rather
than a separate database service. No local `.env`, user database, or broker data
is copied into the image. Background schedulers are disabled by the test entrypoint;
HTTP handlers, authentication, sessions, and schema initialization remain real.

Fixtures create uniquely named accounts. Admin tests promote generated accounts
in the container database without relying on seeded admin credentials. Tests
never invoke live market-data collection or send Telegram alerts.

Unit tests cover security, role guards, schema validation, ID collisions, phone
normalization, and database retry behavior. Integration tests cover API startup,
schema migration idempotence, registration/login/logout, profile reads, permission
checks, Data reads, pagination validation, route naming, and CORS. Live broker,
scraper, training, and notification behavior is not yet covered.

GitHub Actions runs both suites on pushes and pull requests and uploads JUnit
and coverage reports. Production image publication waits for these tests.
On failed push, manual, or same-repository pull request runs, it automatically opens an issue for each failed
or errored test case, with the commit, run link, and failure details. Existing
open issues for the same test prevent duplicates. Fork pull request runs do not create
issues because their tokens have restricted permissions. Setup failures
without JUnit test results do not create test-case issues.
