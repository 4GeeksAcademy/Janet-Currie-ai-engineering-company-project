"""GET /tasks/{task_id} mapping and auth."""

from __future__ import annotations

import pytest

from app.celery_app import BrokerUnavailableError, celery_app
from app.tasks.status import public_status, validate_task_id, InvalidTaskIdError
from tests.helpers import auth_header, client

TASK_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


class _FakeResult:
    def __init__(self, state: str, result=None) -> None:
        self.state = state
        self.result = result


def test_public_status_mapping() -> None:
    assert public_status("PENDING") == "pending"
    assert public_status("RECEIVED") == "pending"
    assert public_status("STARTED") == "started"
    assert public_status("RETRY") == "started"
    assert public_status("SUCCESS") == "success"
    assert public_status("FAILURE") == "failure"
    assert public_status("REVOKED") == "failure"
    assert public_status("CUSTOM") == "pending"
    assert public_status(None) == "pending"


def test_malformed_task_id_rejected() -> None:
    with pytest.raises(InvalidTaskIdError):
        validate_task_id("x")
    with pytest.raises(InvalidTaskIdError):
        validate_task_id("")
    with pytest.raises(InvalidTaskIdError):
        validate_task_id("bad id")


def test_get_task_requires_auth() -> None:
    assert client.get(f"/tasks/{TASK_ID}").status_code == 401


def test_get_task_malformed_is_422() -> None:
    headers = auth_header(email="task-bad@healthcore.example")
    response = client.get("/tasks/nope", headers=headers)
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("state", "public"),
    [
        ("PENDING", "pending"),
        ("RECEIVED", "pending"),
        ("STARTED", "started"),
        ("RETRY", "started"),
        ("FAILURE", "failure"),
        ("REVOKED", "failure"),
    ],
)
def test_get_task_maps_non_success(
    monkeypatch: pytest.MonkeyPatch, state: str, public: str
) -> None:
    monkeypatch.setattr(celery_app, "AsyncResult", lambda _tid: _FakeResult(state, Exception("boom")))
    headers = auth_header(email=f"task-{state.lower()}@healthcore.example")
    response = client.get(f"/tasks/{TASK_ID}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == TASK_ID
    assert body["status"] == public
    assert body["result"] is None
    assert "Traceback" not in str(body)
    assert "boom" not in str(body)


def test_get_task_success_returns_bounded_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        celery_app,
        "AsyncResult",
        lambda _tid: _FakeResult(
            "SUCCESS",
            {
                "run_id": "run-1",
                "status": "completed",
                "month_start": "2026-07-01",
                "records_processed": 4,
                "events_extracted": 4,
                "events_quarantined": 0,
            },
        ),
    )
    headers = auth_header(email="task-ok@healthcore.example")
    response = client.get(f"/tasks/{TASK_ID}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["result"]["run_id"] == "run-1"
    assert body["result"]["records_processed"] == 4


def test_get_task_broker_down_is_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routers.tasks.task_status",
        lambda _tid: (_ for _ in ()).throw(BrokerUnavailableError("down")),
    )
    headers = auth_header(email="task-503@healthcore.example")
    response = client.get(f"/tasks/{TASK_ID}", headers=headers)
    assert response.status_code == 503
