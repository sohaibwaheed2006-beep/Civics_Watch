# Developer 2 - Dependencies

No new runtime or build dependencies are required for the report domain
beyond the pins already in `requirements.txt`:

- fastapi, pydantic (schemas, routing)
- SQLAlchemy, alembic, PyMySQL (persistence, migrations)
- python-multipart (photo uploads)
- argon2-cffi, PyJWT (auth; shared with Developer 1)
- pytest, httpx (tests)

### Optional

- An external AI provider SDK (e.g. `anthropic`, `openai`): required **only**
  if `AI_ENABLED=true` and a non-fallback provider is used. The report domain
  ships with a deterministic classifier that satisfies every endpoint without
  any external call. If you later add a provider, pin it here and expose it
  through the `ai_service` provider abstraction so configuration stays single-
  source.

### Environment variables added

- `MAX_PHOTOS_PER_REPORT` (default `8`)
- `DUPLICATE_RADIUS_METERS` (default `150`)
- `DUPLICATE_TIME_WINDOW_HOURS` (default `168`)
- `DUPLICATE_MIN_SCORE` (default `0.55`)
- `AI_ENABLED` (default `false`)
- `AI_PROVIDER` (default `deterministic`)
- `AI_API_KEY` (default empty)
- `AI_MODEL` (default empty)
- `AI_TIMEOUT_SECONDS` (default `10`)

Existing variables (`UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`) are reused for photo
uploads with no behavioural change for Developer 1 flows.
