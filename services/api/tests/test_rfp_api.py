"""Authenticated RFP upload and ticket reads."""

from __future__ import annotations

from app.celery_app import BrokerUnavailableError
from app.rfp.repository import get_ticket, mark_discarded
from app.rfp.schemas import SAFE_MESSAGES
from app.rfp.storage import declared_too_large, save_pdf
from tests.helpers import auth_header, client, reset_auth_db, reset_inventory_db

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


def _setup(monkeypatch, tmp_path):
    reset_auth_db()
    reset_inventory_db()
    monkeypatch.setattr("app.rfp.storage.raw_directory", lambda: tmp_path)
    monkeypatch.setattr("app.tasks.rfp_intake.enqueue_rfp_intake", lambda ticket_id: "task-1")
    return auth_header()


def _upload(headers, body=PDF, name="request.pdf", content_type="application/pdf"):
    return client.post(
        "/rfp/tickets",
        files={"file": (name, body, content_type)},
        headers=headers,
    )


def test_anonymous_ticket_routes_are_rejected() -> None:
    assert client.post("/rfp/tickets").status_code == 401
    assert client.get("/rfp/tickets").status_code == 401
    assert client.get("/rfp/tickets/missing").status_code == 401


def test_valid_pdf_returns_202_and_opaque_path(monkeypatch, tmp_path) -> None:
    headers = _setup(monkeypatch, tmp_path)
    seen: list[str] = []

    def enqueue(ticket_id: str) -> str:
        seen.append(ticket_id)
        return "task-1"

    monkeypatch.setattr("app.tasks.rfp_intake.enqueue_rfp_intake", enqueue)
    response = _upload(headers, name="../../etc/passwd.pdf")
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "analyzing"
    assert body["processing_state"] == "queued"
    assert seen == [body["ticket_id"]]
    ticket = get_ticket(body["ticket_id"])
    assert ticket is not None
    assert ticket.raw_pdf_path == f"data/raw/{body['ticket_id']}.pdf"
    assert "passwd" not in ticket.raw_pdf_path
    assert (tmp_path / f"{body['ticket_id']}.pdf").is_file()
    assert "raw_pdf_path" not in body


def test_upload_rejects_unsafe_files(monkeypatch, tmp_path) -> None:
    headers = _setup(monkeypatch, tmp_path)
    assert _upload(headers, body=b"").status_code == 400
    assert _upload(headers, body=b"not a pdf").status_code == 400
    assert _upload(headers, content_type="text/plain").status_code == 400
    assert _upload(headers, name="notes.txt").status_code == 400
    response = client.post(
        "/rfp/tickets",
        files=[
            ("file", ("one.pdf", PDF, "application/pdf")),
            ("extra", ("two.pdf", PDF, "application/pdf")),
        ],
        headers=headers,
    )
    assert response.status_code == 400


def test_declared_and_streamed_size_limits_do_not_need_a_full_buffer() -> None:
    assert declared_too_large("99999999", max_bytes=100) is True
    assert declared_too_large("10", max_bytes=100) is False
    try:
        save_pdf("ticket-size", [b"%PDF-123456789"], max_bytes=8)
    except Exception as exc:
        assert getattr(exc, "reason_code", "") == "too_large"
    else:
        raise AssertionError("oversized stream was accepted")


def test_broker_failure_leaves_a_visible_ticket(monkeypatch, tmp_path) -> None:
    headers = _setup(monkeypatch, tmp_path)

    def enqueue(_ticket_id: str) -> str:
        raise BrokerUnavailableError("down")

    monkeypatch.setattr("app.tasks.rfp_intake.enqueue_rfp_intake", enqueue)
    response = _upload(headers)
    assert response.status_code == 503
    body = response.json()
    ticket = get_ticket(body["ticket_id"])
    assert ticket is not None
    assert ticket.processing_state == "failed"
    assert ticket.outcome_reason_code == "processing_failed"
    assert ticket.status == "analyzing"
    assert (tmp_path / f"{body['ticket_id']}.pdf").is_file()


def test_detail_and_list_hide_document_text(monkeypatch, tmp_path) -> None:
    headers = _setup(monkeypatch, tmp_path)
    other = auth_header(email="blair@healthcore.example")
    created = _upload(headers)
    ticket_id = created.json()["ticket_id"]
    detail = client.get(f"/rfp/tickets/{ticket_id}", headers=other)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["message"] == SAFE_MESSAGES["analyzing"]
    assert payload["metadata"] is None
    assert payload["departments"] == []
    assert "passwd" not in detail.text
    listed = client.get("/rfp/tickets", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["ticket_id"] == ticket_id


def test_discarded_reason_uses_a_fixed_message(monkeypatch, tmp_path) -> None:
    headers = _setup(monkeypatch, tmp_path)
    ticket_id = _upload(headers).json()["ticket_id"]
    mark_discarded(
        ticket_id,
        reason_code="phi_detected",
        contains_phi=True,
        requires_compliance_review=True,
    )
    payload = client.get(f"/rfp/tickets/{ticket_id}", headers=headers).json()
    assert payload["status"] == "discarded"
    assert payload["message"] == SAFE_MESSAGES["phi_detected"]
    assert payload["contains_phi"] is True
    assert "patient" not in payload["message"].lower()
