#!/usr/bin/env python
"""Exercise every Celery metric path and print a summary.

Usage (from the example/ directory, with the worker already running):

    uv run python exercise_metrics.py

What it triggers:
    flower.events.total  (task-sent, task-received, task-started,
                          task-succeeded, task-failed, task-retried, task-revoked)
    flower.task.runtime.seconds
    flower.worker.number.of.currently.executing.tasks
    flower.worker.online
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

import django  # noqa: E402

django.setup()

from myproject.tasks import add, fail_task, retry_task, slow_task  # noqa: E402

SEPARATOR = "-" * 60


def section(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def wait_for(result, timeout: int = 15, label: str = "task"):
    """Poll a result until ready or timeout."""
    deadline = time.monotonic() + timeout
    while not result.ready():
        if time.monotonic() > deadline:
            print(f"  ⏱  {label} did not finish within {timeout}s")
            return None
        time.sleep(0.3)
    return result


def main() -> None:
    print("=" * 60)
    print("  Celery Metrics Exercise Script")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Successful tasks  →  task-sent, task-received, task-started,
    #                          task-succeeded, runtime histogram
    # ------------------------------------------------------------------
    section("1. Successful tasks (add)")
    results = [add.delay(i, i + 1) for i in range(5)]
    for i, r in enumerate(results):
        wait_for(r, label=f"add #{i}")
        status = r.status
        value = r.result if status == "SUCCESS" else None
        print(f"  add #{i}: status={status} result={value}")

    # ------------------------------------------------------------------
    # 2. Slow task  →  longer runtime in histogram
    # ------------------------------------------------------------------
    section("2. Slow task (runtime histogram)")
    r = slow_task.delay(2)
    wait_for(r, timeout=10, label="slow_task")
    print(f"  slow_task: status={r.status} result={r.result}")

    # ------------------------------------------------------------------
    # 3. Failing task  →  task-failed event
    # ------------------------------------------------------------------
    section("3. Failing task")
    r = fail_task.delay()
    wait_for(r, label="fail_task")
    print(f"  fail_task: status={r.status}")
    if r.result:
        print(f"  exception: {r.result}")

    # ------------------------------------------------------------------
    # 4. Retrying task  →  task-retried events (×max_retries), then failure
    # ------------------------------------------------------------------
    section("4. Retrying task (3 retries then failure)")
    r = retry_task.delay()
    wait_for(r, timeout=20, label="retry_task")
    print(f"  retry_task: status={r.status}")
    if r.result:
        print(f"  exception: {r.result}")

    # ------------------------------------------------------------------
    # 5. Revoked task  →  task-revoked event
    # ------------------------------------------------------------------
    section("5. Revoked task")
    r = slow_task.delay(30)  # long enough to revoke before it finishes
    time.sleep(0.5)  # let it get queued / received
    r.revoke(terminate=True)
    print(f"  slow_task revoked: id={r.id}")
    time.sleep(2)  # give the worker time to process the revocation

    # ------------------------------------------------------------------
    # 6. Burst of fast tasks  →  concurrent execution gauge
    # ------------------------------------------------------------------
    section("6. Burst of 10 fast tasks (concurrency gauge)")
    burst = [add.delay(i, i * 2) for i in range(10)]
    for i, r in enumerate(burst):
        wait_for(r, label=f"burst #{i}")
    successes = sum(1 for r in burst if r.status == "SUCCESS")
    print(f"  {successes}/10 tasks succeeded")

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    section("Done")
    print("  Check Grafana at http://localhost:3000")
    print("  Metrics are exported every 5s via OTLP.")
    print("  Look for metrics prefixed with 'flower.*'\n")


if __name__ == "__main__":
    sys.exit(main() or 0)
