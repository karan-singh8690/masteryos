"""MasteryOS Python SDK — main client class."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import url_join

import httpx


class APIError(Exception):
    """Raised when the API returns an error."""

    def __init__(self, status_code: int, message: str, code: str | None = None):
        self.status_code = status_code
        self.code = code
        super().__init__(f"[{status_code}] {message}")


class RateLimitError(APIError):
    """Raised when rate limited (429)."""

    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(429, "Rate limited", "RATE_LIMITED")


class LearningResource:
    """Learning endpoints."""

    def __init__(self, client: "MasteryOS"):
        self._client = client

    def get_dashboard(self) -> dict[str, Any]:
        return self._client._get("/api/v1/learning/dashboard")

    def start_session(self, subject_id: str, intent: str = "mixed", target_question_count: int = 10) -> dict[str, Any]:
        return self._client._post("/api/v1/learning/sessions", json={
            "subject_id": subject_id, "intent": intent, "target_question_count": target_question_count,
        })

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._client._get(f"/api/v1/learning/sessions/{session_id}")

    def submit_answer(self, session_id: str, question_id: str, answer: Any) -> dict[str, Any]:
        return self._client._post(f"/api/v1/learning/sessions/{session_id}/answers", json={
            "question_id": question_id, "answer": answer,
        })

    def get_mastery(self) -> dict[str, Any]:
        return self._client._get("/api/v1/learning/mastery")

    def get_recommendations(self) -> dict[str, Any]:
        return self._client._get("/api/v1/learning/recommendations")


class AuthResource:
    """Authentication endpoints."""

    def __init__(self, client: "MasteryOS"):
        self._client = client

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self._client._post("/api/v1/auth/login", json={"email": email, "password": password})

    def register(self, email: str, password: str, display_name: str, invite_token: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"email": email, "password": password, "display_name": display_name}
        if invite_token:
            payload["invite_token"] = invite_token
        return self._client._post("/api/v1/auth/register", json=payload)

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        return self._client._post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    def logout(self) -> dict[str, Any]:
        return self._client._post("/api/v1/auth/logout")


class BetaOpsResource:
    """Beta Operations endpoints (admin)."""

    def __init__(self, client: "MasteryOS"):
        self._client = client

    def get_dashboard(self) -> dict[str, Any]:
        return self._client._get("/api/v1/admin/beta-ops/dashboard")

    def get_funnel(self, days: int = 30) -> dict[str, Any]:
        return self._client._get(f"/api/v1/admin/beta-ops/analytics/funnel?days={days}")

    def get_retention(self, weeks: int = 8) -> list[dict[str, Any]]:
        return self._client._get(f"/api/v1/admin/beta-ops/analytics/retention?weeks={weeks}")

    def get_learning(self) -> dict[str, Any]:
        return self._client._get("/api/v1/admin/beta-ops/learning")

    def get_feedback(self, limit: int = 100) -> dict[str, Any]:
        return self._client._get(f"/api/v1/admin/beta-ops/feedback?limit={limit}")

    def get_user_success(self) -> dict[str, Any]:
        return self._client._get("/api/v1/admin/beta-ops/success")

    def get_instructor(self) -> dict[str, Any]:
        return self._client._get("/api/v1/admin/beta-ops/instructor")

    def get_operations(self) -> dict[str, Any]:
        return self._client._get("/api/v1/admin/beta-ops/operations")

    def get_releases(self) -> dict[str, Any]:
        return self._client._get("/api/v1/admin/beta-ops/releases")

    def get_report(self, period: str = "weekly") -> dict[str, Any]:
        return self._client._get(f"/api/v1/admin/beta-ops/reports/{period}")

    def list_experiments(self) -> list[dict[str, Any]]:
        return self._client._get("/api/v1/admin/beta-ops/experiments")


class MasteryOS:
    """Main MasteryOS client.

    Args:
        api_key: Your API key (find at /portal/api-keys).
        base_url: API base URL (default: https://api.masteryos.com).
        timeout: Request timeout in seconds (default: 30).
        max_retries: Max retry attempts for 5xx errors (default: 3).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.masteryos.com",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"masteryos-python/{__import__('masteryos').__version__}",
            },
        )
        self.learning = LearningResource(self)
        self.auth = AuthResource(self)
        self.beta_ops = BetaOpsResource(self)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self._base_url}{path}"
        for attempt in range(self._max_retries + 1):
            response = self._client.request(method, url, **kwargs)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(int(retry_after) if retry_after else None)
            if response.status_code >= 500 and attempt < self._max_retries:
                time.sleep(2 ** attempt)
                continue
            if response.status_code >= 400:
                try:
                    error = response.json()
                    raise APIError(response.status_code, error.get("detail", response.text), error.get("code"))
                except ValueError:
                    raise APIError(response.status_code, response.text)
            return response.json()

    def _get(self, path: str, **kwargs) -> Any:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs) -> Any:
        return self._request("POST", path, **kwargs)

    def _patch(self, path: str, **kwargs) -> Any:
        return self._request("PATCH", path, **kwargs)

    def _delete(self, path: str, **kwargs) -> Any:
        return self._request("DELETE", path, **kwargs)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
