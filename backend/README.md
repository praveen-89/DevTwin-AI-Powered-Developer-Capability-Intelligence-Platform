# DevTwin Backend — Development Setup Guide

## Python Requirement

**IMPORTANT**: This backend requires the **official Windows CPython interpreter** from
[python.org](https://www.python.org/downloads/windows/), **not** the MSYS2/MinGW Python.

The MSYS2 Python cannot install `pydantic-core` or `pydantic v2` because:
- `pydantic-core` requires `maturin` (a Rust build tool)
- `maturin` requires Cargo ≥ 1.85 (edition2024 support)
- PyPI pre-built wheels target `cp311-cp311-win_amd64` (official CPython), not `mingw_x86_64-cpython-311`

### Install Official CPython

1. Download Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/)
2. Run the installer — tick "Add Python to PATH"
3. Verify: `python --version` should show `[MSC ...]` not `[GCC ...]`

## Quick Start

```powershell
# From the backend/ directory:

# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in environment variables
copy ..\.env.example ..\.env
# Edit .env with your Supabase credentials

# 5. Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Run tests
pytest tests/ -v
```

## Environment Variables

Copy `../.env.example` to `../.env` and fill in:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase transaction-mode pooler URL (postgresql+asyncpg://...) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon (public) key |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key — **keep secret, never expose to frontend** |
| `SECRET_KEY` | Internal signing secret — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CORS_ORIGINS` | Comma-separated allowed origins (default: `http://localhost:3000`) |
| `DEBUG` | Set to `true` in development to enable `/docs`, `false` in production |

## Running Database Migrations

Apply migrations to your Supabase project via the Supabase SQL Editor or CLI:

```bash
# Using Supabase CLI:
supabase db push

# Or manually via the Supabase Dashboard SQL Editor:
# 1. Open: database/migrations/001_initial_schema.sql — run it
# 2. Open: database/migrations/002_rls_policies.sql — run it
# 3. Open: database/migrations/003_v01_foundation.sql — run it
# 4. Open: database/migrations/004_v02_auth_github.sql — run it
```

## API Endpoints (v0.2 Foundation)

### Implemented foundation

* `GET /health` — API liveness check (no DB required)
* `GET /health/database` — DB readiness check
* Supabase JWT/JWKS authentication foundation
* authenticated-user dependency
* authenticated-developer lookup dependency

**Planned / Not Yet Implemented:**
* `POST /developers/me` is planned/next and is NOT implemented yet.
* GitHub integration is planned and is NOT implemented yet.

## Testing

```powershell
# Unit tests (no live DB required — DB is mocked)
pytest tests/ -v

# With coverage (if coverage installed)
pytest tests/ -v --cov=app
```
