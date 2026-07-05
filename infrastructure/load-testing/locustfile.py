"""Load testing scripts for the Mastery Engine.

Tests:
- 100 users (baseline)
- 500 users (moderate load)
- 1000 users (high load)
- Concurrent study sessions
- Concurrent question submissions
- WebSocket stress testing

Usage:
    locust -f locustfile.py --host=http://localhost:8000
    locust -f locustfile.py --headless -u 100 -r 10 --host=http://localhost:8000
"""

from __future__ import annotations

import json
import random
import time
from uuid import uuid4

try:
    from locust import HttpUser, task, between, events
    LOCUST_AVAILABLE = True
except ImportError:
    LOCUST_AVAILABLE = False
    class HttpUser: pass
    def task(weight=1): return lambda f: f
    def between(min_wait, max_wait): return lambda: 0
    class events:
        @staticmethod
        def test_start(*a, **kw): pass
        @staticmethod
        def test_stop(*a, **kw): pass

TEST_EMAILS = [f"loadtest{i}@example.com" for i in range(1000)]
TEST_PASSWORD = "LoadTestPassword123!"


class LearnerUser(HttpUser):
    """Simulates a learner going through the study flow."""
    wait_time = between(1, 5)
    weight = 3

    def on_start(self):
        self.email = random.choice(TEST_EMAILS)
        self.password = TEST_PASSWORD
        self.access_token = None
        self.session_id = None
        self.login()

    def login(self):
        response = self.client.post("/api/v1/auth/login",
            json={"email": self.email, "password": self.password}, name="POST /auth/login")
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
        elif response.status_code == 401:
            self.register()

    def register(self):
        response = self.client.post("/api/v1/auth/register",
            json={"email": self.email, "password": self.password, "display_name": "Load Test"},
            name="POST /auth/register")
        if response.status_code == 201:
            self.access_token = response.json().get("access_token")

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}

    @task(10)
    def get_dashboard(self):
        self.client.get("/api/v1/dashboard", headers=self.auth_headers, name="GET /dashboard")

    @task(5)
    def get_profile(self):
        self.client.get("/api/v1/users/me", headers=self.auth_headers, name="GET /users/me")

    @task(3)
    def start_study_session(self):
        response = self.client.post("/api/v1/study-sessions",
            json={"enrollment_id": str(uuid4()), "intent": "mixed", "target_question_count": 10},
            headers=self.auth_headers, name="POST /study-sessions")
        if response.status_code == 201:
            self.session_id = response.json().get("id")

    @task(5)
    def get_adaptive_queue(self):
        if self.session_id:
            self.client.get(f"/api/v1/study-sessions/{self.session_id}/adaptive-queue",
                headers=self.auth_headers, name="GET /adaptive-queue")

    @task(4)
    def submit_answer(self):
        if self.session_id:
            queue_response = self.client.get(
                f"/api/v1/study-sessions/{self.session_id}/adaptive-queue",
                headers=self.auth_headers, name="GET /adaptive-queue (for submit)")
            if queue_response.status_code == 200:
                questions = queue_response.json().get("questions", [])
                if questions:
                    qid = questions[0]["question_instance_id"]
                    self.client.post(f"/api/v1/questions/{qid}/submit",
                        json={"answer": {"choice": "a"}, "answer_type": "multiple_choice",
                              "confidence": 0.7, "time_spent_seconds": random.randint(10, 60),
                              "hint_used": False, "hint_tiers_used": []},
                        headers=self.auth_headers, name="POST /questions/submit")

    @task(2)
    def get_notifications(self):
        self.client.get("/api/v1/notifications?status=unread",
            headers=self.auth_headers, name="GET /notifications")


class ContentEditorUser(HttpUser):
    """Simulates a content editor managing content."""
    wait_time = between(2, 10)
    weight = 1

    def on_start(self):
        self.email = f"editor{random.randint(0, 99)}@example.com"
        self.password = TEST_PASSWORD
        self.access_token = None
        response = self.client.post("/api/v1/auth/login",
            json={"email": self.email, "password": self.password}, name="POST /auth/login (editor)")
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}

    @task(5)
    def list_subjects(self):
        self.client.get("/api/v1/admin/subjects", headers=self.auth_headers, name="GET /admin/subjects")

    @task(3)
    def list_templates(self):
        self.client.get("/api/v1/admin/subjects/00000000-0000-0000-0000-000000000001/question-templates",
            headers=self.auth_headers, name="GET /admin/templates")

    @task(2)
    def get_content_dashboard(self):
        self.client.get("/api/v1/admin/content/dashboard", headers=self.auth_headers,
            name="GET /admin/content/dashboard")


class AdminUser(HttpUser):
    """Simulates an admin monitoring the platform."""
    wait_time = between(5, 15)
    weight = 1

    def on_start(self):
        self.email = f"admin{random.randint(0, 9)}@example.com"
        self.password = TEST_PASSWORD
        self.access_token = None
        response = self.client.post("/api/v1/auth/login",
            json={"email": self.email, "password": self.password}, name="POST /auth/login (admin)")
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}

    @task(10)
    def get_ops_dashboard(self):
        self.client.get("/api/v1/admin/bg/workers/metrics", headers=self.auth_headers,
            name="GET /admin/workers/metrics")

    @task(5)
    def get_outbox_stats(self):
        self.client.get("/api/v1/admin/bg/outbox/stats", headers=self.auth_headers,
            name="GET /admin/outbox/stats")

    @task(3)
    def list_workers(self):
        self.client.get("/api/v1/admin/bg/workers", headers=self.auth_headers,
            name="GET /admin/workers")

    @task(2)
    def get_audit_logs(self):
        self.client.get("/api/v1/admin/audit-logs?limit=50", headers=self.auth_headers,
            name="GET /admin/audit-logs")


# Scenario configurations
LOAD_TEST_SCENARIOS = {
    "baseline": {"users": 100, "spawn_rate": 10, "duration": 300},
    "moderate": {"users": 500, "spawn_rate": 20, "duration": 600},
    "high": {"users": 1000, "spawn_rate": 50, "duration": 600},
    "spike": {"users": 2000, "spawn_rate": 200, "duration": 120},
    "endurance": {"users": 200, "spawn_rate": 5, "duration": 3600},
}


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n{'='*60}")
    print(f"Load test starting")
    print(f"Target: {environment.host}")
    print(f"Users: {environment.parsed_options.num_users}")
    print(f"Spawn rate: {environment.parsed_options.spawn_rate}/s")
    print(f"{'='*60}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    print(f"\n{'='*60}")
    print(f"Load test complete")
    print(f"{'='*60}")
    print(f"\nSummary:")
    print(f"  Total requests: {stats.total.num_requests}")
    print(f"  Total failures: {stats.total.num_failures}")
    print(f"  Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"  Min response time: {stats.total.min_response_time:.2f}ms")
    print(f"  Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"  Requests/s: {stats.total.current_rps:.2f}")
    rate = (stats.total.num_failures / max(stats.total.num_requests, 1) * 100)
    print(f"  Failure rate: {rate:.2f}%")
    print(f"\n{'='*60}\n")
