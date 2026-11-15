# Secure Webhook Processing API

A FastAPI service that receives webhook events, verifies their HMAC-SHA256
signature, prevents duplicate processing, and stores events in PostgreSQL.

All event data in this project is simulated. No real payments are processed.

## Prerequisites

- Docker and Docker Compose v2
- Python 3.11+ (3.12 recommended), only needed to run tests and the demo script
- Git

## Setup

1. Clone the repository and open the project folder.
2. Create your local configuration file:

   ```
   cp .env.example .env
   ```

   On Windows PowerShell use `Copy-Item .env.example .env`.

3. Open `.env` and set real local values:
   - `POSTGRES_PASSWORD`: choose a password using **letters and numbers only**
     (characters such as `$` break Docker Compose).
   - Use the **same password** inside `DATABASE_URL`.
   - `WEBHOOK_SECRET`: generate one with
     `python -c "import secrets; print(secrets.token_hex(32))"`.

`.env` is ignored by Git. Never commit real credentials.

### Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Database connection used when running on your machine (tests, demo, local runs) |
| `WEBHOOK_SECRET` | Shared secret used to verify signatures |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credentials used to create the PostgreSQL container |

If `DATABASE_URL` or `WEBHOOK_SECRET` is missing, the service refuses to start
with an error that names the missing setting.

## Run with Docker Compose

```
docker compose up -d --build
```

This starts three services:

- `db`: PostgreSQL 16 (published on host port **5433** to avoid clashing with a
  local PostgreSQL on 5432)
- `migrate`: runs the database migrations once and exits (exit code 0 is normal)
- `api`: the FastAPI service on http://127.0.0.1:8000

Check status with `docker compose ps -a`. Interactive API docs are available at
http://127.0.0.1:8000/docs.

Stop everything with `docker compose down` (add `-v` to also delete the data).

## Migrations

Migrations use Alembic and run automatically through the `migrate` service.
To run them manually from your machine:

```
alembic upgrade head
```

## Endpoint

`POST /webhooks`

Headers:

```
Content-Type: application/json
X-Webhook-Signature: sha256=<hex_digest>
```

The signature is HMAC-SHA256 over the **exact raw request body bytes**, using
`WEBHOOK_SECRET`. Do not re-serialize the JSON after signing.

Example body:

```json
{
  "event_id": "evt_test_1001",
  "event_type": "payment.completed",
  "created_at": "2026-11-08T10:30:00Z",
  "data": {
    "payment_id": "pay_test_5001",
    "amount": 2500,
    "currency": "USD",
    "status": "completed"
  }
}
```

Required fields: `event_id` (text, max 255), `event_type` (text, max 100),
`created_at` (ISO 8601 timestamp), `data` (JSON object).

### Response codes

| Situation | Status | Body |
|---|---|---|
| First valid delivery | 200 | `{"status": "processed", "event_id": "..."}` |
| Duplicate `event_id` | 200 | `{"status": "duplicate", "event_id": "..."}` |
| Missing or invalid signature | 401 | `{"detail": "Invalid or missing signature"}` |
| Malformed JSON or invalid payload | 422 | `{"detail": [...]}` (list of validation errors) |
| Database failure | 500 | `{"detail": "Internal server error"}` |

Duplicates return 200 on purpose: senders usually retry on errors, and a
duplicate is not an error. Duplicate deliveries are never processed twice.

### Try it

With the service running, this script sends signed and unsigned requests and
prints each result (first delivery, duplicate, wrong signature, missing
signature, invalid payloads):

```
python -m scripts.demo
```

To sign a request yourself:

```python
import hashlib, hmac
body = b'{"event_id": "evt_1", ...}'   # the exact bytes you send
signature = "sha256=" + hmac.new(b"<WEBHOOK_SECRET>", body, hashlib.sha256).hexdigest()
```

## How idempotency works

- `webhook_events.event_id` has a database-level `UNIQUE` constraint.
- Each request runs one transaction using `INSERT ... ON CONFLICT DO NOTHING`.
  Simultaneous requests with the same `event_id` cannot both be accepted.
- Recording the event and marking it `processed` happen in the **same
  transaction**. If the service stops before the commit, nothing is saved, and
  the sender's retry is processed normally. There is no event stuck in
  `received` after a crash.
- On a database failure the transaction is rolled back and the service returns
  500, never a false success.

## Run the tests

1. Start the database: `docker compose up -d db`
2. Create the test database once:

   ```
   docker compose exec db psql -U <POSTGRES_USER> -d <POSTGRES_DB> -c "CREATE DATABASE webhook_test_db;"
   ```

3. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   .venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Run the tests:

   ```
   pytest -v
   ```

The tests use `webhook_test_db` and never touch your main database. They cover:
valid signature, invalid signature, missing signature, repeated `event_id`,
concurrent duplicate requests, malformed payload, database failure with
rollback, and missing configuration at startup.

## Security notes

- Signatures are compared in constant time (`hmac.compare_digest`) over the raw
  body bytes.
- Secrets come from environment variables only.
- Logs never contain secrets, signatures, or payload values.
- The container runs as a non-root user.

## Known limitations

- **No replay protection.** `created_at` is stored but not checked for
  freshness, so a captured valid request could be replayed. Duplicate
  `event_id` values are still ignored. Timestamp-window protection is outside
  the agreed scope and would need a separate estimate.
- Processing is a simple isolated function (`app/processing.py`). There is no
  queue or background worker.
- Simulated payment events only: no real payments, refunds, or subscriptions.
- No frontend, cloud deployment, or compliance certification.