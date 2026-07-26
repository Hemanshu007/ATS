"""
Locust load test: WARM cache — GET /jobs/

Cache must be primed before running this test (e.g. via the API once per
query shape). All requests within the 60s TTL hit Redis.

Run: locust -f locust_warm.py --headless -u 50 -r 5 --run-time 30s
"""
from locust import HttpUser, task, between


class WarmCacheUser(HttpUser):
    wait_time = between(0.05, 0.2)

    @task(5)
    def page1(self):
        self.client.get("/jobs/?page=1&page_size=20", name="GET /jobs/ page=1 [WARM]")

    @task(3)
    def page2(self):
        self.client.get("/jobs/?page=2&page_size=20", name="GET /jobs/ page=2 [WARM]")

    @task(2)
    def page3(self):
        self.client.get("/jobs/?page=3&page_size=20", name="GET /jobs/ page=3 [WARM]")

    @task(1)
    def filtered(self):
        self.client.get("/jobs/?page=1&page_size=20&job_type=remote", name="GET /jobs/ filtered [WARM]")
