import time

from celery import shared_task


@shared_task
def add(x, y):
    """A simple task that adds two numbers."""
    time.sleep(0.5)  # simulate some work
    return x + y


@shared_task
def slow_task(seconds=2):
    """A task that takes a while, useful for testing runtime histograms."""
    time.sleep(seconds)
    return f"slept {seconds}s"


@shared_task(bind=True, max_retries=3)
def retry_task(self):
    """A task that always retries until max_retries is hit."""
    try:
        raise ConnectionError("Simulated transient error")
    except ConnectionError as exc:
        raise self.retry(exc=exc, countdown=1)


@shared_task
def fail_task():
    """A task that always fails, to test error tracing."""
    raise ValueError("Intentional failure for testing")
