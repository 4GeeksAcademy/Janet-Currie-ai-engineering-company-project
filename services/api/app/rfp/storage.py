"""Opaque PDF storage under the repository data/raw directory."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

PDF_MAGIC = b"%PDF-"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MULTIPART_OVERHEAD = 64 * 1024


class UploadRejected(ValueError):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def raw_directory() -> Path:
    path = repo_root() / "data" / "raw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_pdf_path(ticket_id: str) -> str:
    _require_ticket_id(ticket_id)
    return f"data/raw/{ticket_id}.pdf"


def absolute_pdf_path(relative: str) -> Path:
    name = Path(relative).name
    if relative != f"data/raw/{name}":
        raise UploadRejected("unsafe_path")
    _require_ticket_id(name.removesuffix(".pdf"))
    if not name.endswith(".pdf"):
        raise UploadRejected("unsafe_path")
    return raw_directory() / name


def declared_too_large(content_length: str | None, max_bytes: int | None = None) -> bool:
    limit = MAX_UPLOAD_BYTES if max_bytes is None else max_bytes
    if content_length is None or not str(content_length).strip():
        return False
    try:
        declared = int(content_length)
    except (TypeError, ValueError):
        return True
    return declared > limit + MULTIPART_OVERHEAD


def save_pdf(
    ticket_id: str,
    chunks,
    *,
    max_bytes: int | None = None,
) -> str:
    """Stream chunks to a temp file, then rename. The original filename is never used."""

    relative = relative_pdf_path(ticket_id)
    target = absolute_pdf_path(relative)
    limit = MAX_UPLOAD_BYTES if max_bytes is None else max_bytes
    temporary = target.with_name(f"{ticket_id}.pdf.tmp.{uuid4().hex}")
    total = 0
    prefix = b""
    try:
        with temporary.open("wb") as handle:
            for chunk in chunks:
                if not chunk:
                    continue
                total += len(chunk)
                if total > limit:
                    raise UploadRejected("too_large")
                if len(prefix) < 5:
                    prefix += chunk[: 5 - len(prefix)]
                handle.write(chunk)
        if total == 0:
            raise UploadRejected("empty")
        if not prefix.startswith(PDF_MAGIC):
            raise UploadRejected("bad_signature")
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return relative


def delete_stored(relative: str | None) -> None:
    if not relative:
        return
    try:
        path = absolute_pdf_path(relative)
    except UploadRejected:
        return
    path.unlink(missing_ok=True)


def filename_allowed(filename: str | None) -> bool:
    if not filename:
        return False
    name = Path(filename).name
    return name.lower().endswith(".pdf") and not name.lower().endswith(".pdf.exe")


def _require_ticket_id(ticket_id: str) -> None:
    if not ticket_id or "/" in ticket_id or "\\" in ticket_id or ticket_id.startswith("."):
        raise UploadRejected("unsafe_path")
