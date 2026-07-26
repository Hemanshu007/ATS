"""
Locust load test: POST /applications/ — write path + Celery dispatch.

Each virtual user registers a candidate, logs in, and applies to a job
with a synthetic PDF resume. Tests DB write throughput + task queue.

Run: locust -f locust_write.py --headless -u 20 -r 2 --run-time 30s
"""
import random
import string
from locust import HttpUser, task, between

# Minimal valid PDF
_FAKE_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj\n"
    b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (Test Resume) Tj ET\nendstream\nendobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000058 00000 n \n0000000115 00000 n \n0000000266 00000 n \n"
    b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n360\n%%EOF"
)

# Use a fixed set of jobs for applications
JOB_IDS = [
    "909cb391-7291-4978-b883-ecfee6fee834",  # Senior Python Developer
    "7f47b587-9632-4ad6-94d1-8c8a0d5150b5",  # ML Engineer
]


class ApplicationWriteUser(HttpUser):
    wait_time = between(0.3, 0.8)

    def on_start(self):
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.email = f"writetest_{suffix}@example.com"
        self.token = None

        resp = self.client.post("/auth/register", json={
            "email": self.email,
            "password": "LoadTest123!",
            "role": "candidate",
            "name": f"Write Tester {suffix}",
        })
        if resp.status_code == 201:
            resp2 = self.client.post("/auth/login", json={
                "email": self.email,
                "password": "LoadTest123!",
            })
            if resp2.status_code == 200:
                self.token = resp2.json()["access_token"]

    @task
    def apply_to_job(self):
        if not self.token:
            return

        job_id = random.choice(JOB_IDS)
        self.client.post(
            "/applications/",
            headers={"Authorization": f"Bearer {self.token}"},
            files={"resume": ("resume.pdf", _FAKE_PDF, "application/pdf")},
            data={"job_id": job_id},
            name="POST /applications/ [WRITE]",
        )
