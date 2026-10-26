"""Taskboard: a tiny task tracker backed by PostgreSQL.

Endpoints
  GET    /                 HTML UI
  GET    /api/tasks        list tasks
  POST   /api/tasks        create a task      {"title": "..."}
  PATCH  /api/tasks/{id}   update a task      {"done": true}
  DELETE /api/tasks/{id}   delete a task
  GET    /healthz          liveness  (process is up)
  GET    /readyz           readiness (database reachable)
  GET    /metrics          Prometheus metrics
"""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

from . import db

APP_VERSION = os.environ.get("APP_VERSION", "dev")

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)
TASKS = Gauge("taskboard_tasks", "Tasks currently stored", ["state"])
APP_INFO = Gauge("taskboard_info", "Build information", ["version"])
APP_INFO.labels(version=APP_VERSION).set(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.open_pool()
    yield
    db.close_pool()


app = FastAPI(title="Taskboard", version=APP_VERSION, lifespan=lifespan)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # Use the route template (/api/tasks/{task_id}) rather than the raw URL
        # so every task id doesn't become its own time series.
        route = request.scope.get("route")
        path = route.path if route else "unmatched"
        if path != "/metrics":
            HTTP_REQUESTS.labels(request.method, path, str(status)).inc()
            HTTP_LATENCY.labels(request.method, path).observe(time.perf_counter() - start)


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    done: bool | None = None


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "index.html").read_text()


@app.get("/api/tasks")
def list_tasks():
    with db.connection() as conn:
        return conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()


@app.post("/api/tasks", status_code=201)
def create_task(task: TaskIn):
    with db.connection() as conn:
        return conn.execute(
            "INSERT INTO tasks (title) VALUES (%s) RETURNING *", (task.title,)
        ).fetchone()


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    with db.connection() as conn:
        row = conn.execute(
            """
            UPDATE tasks
               SET title = COALESCE(%s, title),
                   done  = COALESCE(%s, done)
             WHERE id = %s
         RETURNING *
            """,
            (update.title, update.done, task_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="task not found")
    return row


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with db.connection() as conn:
        deleted = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,)).rowcount
    if not deleted:
        raise HTTPException(status_code=404, detail="task not found")
    return Response(status_code=204)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/readyz")
def readyz():
    try:
        with db.connection() as conn:
            conn.execute("SELECT 1")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    try:
        with db.connection() as conn:
            row = conn.execute(
                "SELECT count(*) FILTER (WHERE done) AS done,"
                "       count(*) FILTER (WHERE NOT done) AS open FROM tasks"
            ).fetchone()
        TASKS.labels("done").set(row["done"])
        TASKS.labels("open").set(row["open"])
    except Exception:
        pass  # still serve the process metrics if the database is down
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
