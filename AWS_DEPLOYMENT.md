# AWS persistence and hourly predictions

The Docker image starts the backend-owned hourly scheduler by default. The UI
does not need to be open for scheduled predictions.

## Required AWS environment variables

- `TODRINQ_DYNAMODB_TABLE=todrinq-platform-history`: recommended for the current
  AWS App Runner deployment. DynamoDB is the selected production backend when set.
- `TODRINQ_DATABASE_URL`: optional PostgreSQL alternative; ignored when the
  DynamoDB table variable is present.
- `TODRINQ_APP_PASSWORD`: operator login password (secret).
- `TODRINQ_API_TOKEN`: API token (secret).
- `TODRINQ_SESSION_SECRET`: long random cookie-signing secret.
- `TODRINQ_SCHEDULER_ENABLED=true`: enabled by default in the Dockerfile.
- `TODRINQ_COOKIE_SECURE=true`: required behind the AWS HTTPS endpoint.

Optional FIWARE variables remain `ORION_LD_URL`, `SERVICE`, and `SERVICE_PATH`.

## Runtime behaviour

At application startup the database schema is created idempotently. At most one
AWS instance claims each UTC clock-hour through the `scheduler_runs` table. The
cycle runs the available trained models for SoSe #9, SoSe #8, CT, bromate, and
microbial removal and writes every output to `observations`. Distribution SoSe
#11 is not fabricated while its model remains under evaluation.

The `risk_signals` table stores distinct prediction timestamps and preserves the
three-consecutive-high confirmation rule across container restarts. Reassessing
the same prediction timestamp updates the existing signal and cannot increment
the count.

Use the protected `GET /observations/status` endpoint to verify the selected
database backend, observation count, and scheduler status. Public `GET /healthz`
also reports database health for the AWS service health check.

Without `TODRINQ_DATABASE_URL`, the application deliberately falls back to the
local SQLite file for workstation development. Do not use container-local SQLite
as the production AWS history database.
