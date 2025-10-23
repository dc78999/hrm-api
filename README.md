# hrm-api

# Description

A concise API for Human Resource Management (HRM) logic implemented with FastAPI.


# Environment Setup

- Requirements:
  - Linux / macOS
  - Python 3.10+
  - Docker (optional, for containerized run)

- Install locally (example):
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt

- Configuration:
  - The per-organization column configuration is stored in config/columns.json.
  - Database: a lightweight sqlite DB is auto-created at first run at data/users.db.
  - Secrets: none required for the demo. For production, put secrets in environment variables.

# Testing

- Unit tests use pytest and FastAPI TestClient.
  - Run tests:
    - pytest

# Security

- No sensitive attributes are returned unless explicitly allowed by the organization's column config.
- Rate-limiting is implemented in-process to mitigate abuse. For production, use distributed rate limiting.
- Keep production DB credentials and secrets out of the repo and use a secrets manager.

# Contribution

- Fork, implement features in feature branches, run linters & tests, and open a PR.
- Add tests for any new behavior.

# Contact

For questions or issues, contact: dev-team@example.com

# Run & Build

- Run locally:
  - uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

- Build and run with Docker:
  - docker build -t hrm-api .
  - docker run -p 8000:8000 hrm-api

# Notes

- OpenAPI schema is available at /openapi.json and interactive docs at /docs.
- The repository link placeholder: https://github.com/yourusername/hrm-api
