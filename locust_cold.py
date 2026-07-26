"""
Locust load test: COLD cache — GET /jobs/

Uses unique page numbers per user instance so each request creates a new
cache key that nobody else will hit. This guarantees every request is a
cache miss that goes to PostgreSQL — no per-request Redis flush needed.

Run: locust -f locust_cold.py --headless -u 50 -r 5 --run-time 30s
"""
import itertools
from locust import HttpUser, task, between
import threading

_counter = itertools.count(1)
_lock = threading.Lock()


class ColdCacheUser(HttpUser):
    wait_time = between(0.05, 0.2)

    def on_start(self):
        with _lock:
            self._page = next(_counter) % 200 + 1

    @task(5)
    def page(self):
        self.client.get(
            f"/jobs/?page={self._page}&page_size=20",
            name="GET /jobs/ page=N [COLD]",
        )

    @task(1)
    def filtered(self):
        self.client.get(
            f"/jobs/?page={self._page}&page_size=20&job_type=remote",
            name="GET /jobs/ filtered [COLD]",
        )
