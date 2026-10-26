"""Insert fake tasks so there is real data to back up, restore and graph.

DATABASE_URL=postgresql://app:app@localhost:5432/app python -m scripts.seed 5000
"""

import random
import sys

import psycopg

from app.db import SCHEMA, database_url

VERBS = ["Write", "Review", "Fix", "Deploy", "Test", "Document", "Refactor", "Monitor"]
THINGS = [
    "Dockerfile",
    "workflow",
    "playbook",
    "dashboard",
    "alert rule",
    "backup job",
    "Terraform module",
    "README",
    "migration",
    "exporter",
]


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    rows = [
        (f"{random.choice(VERBS)} the {random.choice(THINGS)} #{i}", random.random() < 0.4)
        for i in range(count)
    ]
    with psycopg.connect(database_url()) as conn:
        conn.execute(SCHEMA)
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO tasks (title, done) VALUES (%s, %s)", rows)
    print(f"inserted {count} tasks")


if __name__ == "__main__":
    main()
