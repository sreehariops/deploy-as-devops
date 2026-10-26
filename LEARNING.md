# Learning roadmap

You build everything in this file yourself. Each phase ends with a **"done when"**
check: don't move on until it passes. Ask for the next phase's detailed
instructions when you get there.

Target layout by the end (you create all of it):

```
learnit/
├── app/  tests/  scripts/        # given: the application
├── Dockerfile                    # phase 1
├── .dockerignore                 # phase 1
├── compose.yaml                  # phase 2
├── .github/workflows/            # phase 3, 8
├── monitoring/                   # phase 4  (prometheus.yml, alert rules, grafana provisioning)
├── backup/                       # phase 5  (backup + restore scripts)
├── terraform/                    # phase 6
└── ansible/                      # phase 7  (inventory, roles, playbooks)
```

---

## Phase 1 — Docker: containerise the app
Learn: images vs containers, layers and caching, `FROM`/`COPY`/`RUN`/`CMD`,
multi-stage builds, running as non-root, `.dockerignore`, `HEALTHCHECK`,
networks, volumes, environment variables.

- Run Postgres with `docker run` + a named volume; connect with `psql` inside it.
- Write a `Dockerfile` for the app (python:3.12-slim, non-root user,
  requirements installed before copying code so the layer caches).
- Run the app container on the same user-defined network as Postgres.

**Done when:** `docker image ls` shows your image under ~200 MB, the UI works at
http://localhost:8000, and data survives `docker rm -f` of the Postgres container.

## Phase 2 — Docker Compose: the whole stack in one file
Learn: services, `depends_on` with `condition: service_healthy`, healthchecks,
named volumes, `.env` files, profiles, `docker compose logs/exec/ps`.

**Done when:** `docker compose up -d` from a clean clone brings up app + db, and
`docker compose down` (without `-v`) keeps your data.

## Phase 3 — GitHub Actions: CI
Learn: workflows, triggers, jobs, steps, `services:` containers, caching,
matrix builds, secrets, `GITHUB_TOKEN` permissions, pushing to GHCR, image tags
from git SHA, branch protection.

- Job 1: `ruff check` + `pytest` against a Postgres service container.
- Job 2 (only on `main`, needs job 1): build and push the image to
  `ghcr.io/<you>/taskboard:<sha>` and `:latest`, passing `APP_VERSION`.

**Done when:** a PR with a failing test is blocked, and a merge to `main` produces
a new image whose `/healthz` reports the commit SHA.

## Phase 4 — Prometheus + Grafana: observability
Learn: pull-based scraping, `prometheus.yml`, targets and labels, metric types
(counter, gauge, histogram), PromQL (`rate`, `sum by`, `histogram_quantile`),
recording and alerting rules, Alertmanager, exporters, Grafana data sources,
dashboards and **provisioning as code**.

The app already exposes `/metrics`: `http_requests_total`,
`http_request_duration_seconds`, `taskboard_tasks{state}`, `taskboard_info`.
Add to compose: Prometheus, Grafana, `postgres_exporter`, `node_exporter`,
`cAdvisor`, Alertmanager.

**Done when:** a provisioned Grafana dashboard (committed as JSON) shows request
rate, p95 latency, error rate, task counts, DB connections and DB size; and
stopping Postgres fires an alert within 2 minutes.

## Phase 5 — PostgreSQL backups, retention and restore
Learn: `pg_dump` (custom format) vs `pg_dumpall` vs physical backups
(`pg_basebackup`, WAL archiving, point-in-time recovery), retention policies
(e.g. 7 daily / 4 weekly / 6 monthly), off-site copies, restore drills,
backup monitoring.

- Generate data: `python scripts/seed.py 50000`.
- Scheduled `pg_dump` job with a retention policy that prunes old dumps.
- A restore script that restores into a **fresh** database and checks row counts.
- Expose "last successful backup" as a metric and alert when it is > 26h old.
- Stretch: pgBackRest or WAL-G with point-in-time recovery.

**Done when:** you drop the `tasks` table, restore from last night's backup, and
the app works again — and you've written down how long it took.

## Phase 6 — Terraform: infrastructure as code
Learn: providers, resources, data sources, variables/outputs, state and remote
state with locking, `plan`/`apply`/`destroy`, modules, workspaces or per-env
folders, `terraform fmt/validate`, importing existing resources.

Provision: a VM, network/firewall rules (22 from your IP only, 80/443 public,
3000/9090 not public), an SSH key, an object-storage bucket for backups with a
**lifecycle rule** that enforces retention, and remote state.

**Done when:** `terraform destroy && terraform apply` recreates everything with no
manual clicks, and outputs the VM's IP.

## Phase 7 — Ansible: configure the server and deploy
Learn: inventory (static, then generated from Terraform output), ad-hoc
commands, playbooks, idempotency, roles, handlers, templates (Jinja2),
variables and precedence, `ansible-vault` for secrets, `--check --diff`.

Roles: `common` (users, packages, firewall, unattended upgrades), `docker`,
`taskboard` (templated compose file + `.env` from vault), `monitoring`, `backup`
(cron/systemd timer + upload to the Terraform bucket).

**Done when:** running the playbook twice reports `changed=0` the second time, and a
brand-new VM goes from nothing to serving the app with one command.

## Phase 8 — Put it together: continuous delivery
Learn: environments and required reviewers, OIDC to the cloud (no long-lived
keys), `terraform plan` as a PR comment, deploy jobs, rollbacks by image tag.

**Done when:** merging to `main` tests, builds, pushes, and deploys to the VM; and
you can roll back to the previous version by re-running one workflow with an
older tag.
