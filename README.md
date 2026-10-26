# Taskboard

A deliberately small task tracker (FastAPI + PostgreSQL) used as the workload for
learning Docker, GitHub Actions, Prometheus, Grafana, Terraform and Ansible.
The roadmap is in [LEARNING.md](LEARNING.md).

## What the app does

| Endpoint                 | Purpose                                         |
|--------------------------|-------------------------------------------------|
| `GET /`                  | Web UI                                          |
| `GET/POST /api/tasks`    | List / create tasks                             |
| `PATCH/DELETE /api/tasks/{id}` | Update / delete a task                    |
| `GET /healthz`           | Liveness: the process is up (returns version)  |
| `GET /readyz`            | Readiness: the database is reachable (503 if not) |
| `GET /metrics`           | Prometheus metrics                              |

The table is created automatically on startup.

## Configuration (environment variables only)

| Variable       | Default | Notes                                              |
|----------------|---------|----------------------------------------------------|
| `DATABASE_URL` | none    | required, e.g. `postgresql://app:app@db:5432/app`  |
| `DB_POOL_SIZE` | `5`     | max connections from the app                       |
| `APP_VERSION`  | `dev`   | shown in `/healthz` and `taskboard_info` metric    |

## Commands you'll need

```bash
pip install -r requirements.txt               # runtime deps
pip install -r requirements-dev.txt           # + pytest, ruff
uvicorn app.main:app --host 0.0.0.0 --port 8000
ruff check . && ruff format --check .         # lint
pytest -q                                     # tests (need a real Postgres via DATABASE_URL)
python -m scripts.seed 10000                  # insert fake rows
```

## Metrics exposed

- `http_requests_total{method,path,status}`: counter
- `http_request_duration_seconds{method,path}`: histogram
- `taskboard_tasks{state="open"|"done"}`: gauge
- `taskboard_info{version}`: always 1, carries the version label
- plus Python process metrics (`process_*`, `python_*`)
