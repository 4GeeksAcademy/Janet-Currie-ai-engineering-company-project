"""PDF to Markdown. The result stays in memory until the privacy gate clears it."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path

PDF_MAGIC = b"%PDF-"
CONVERT_TIMEOUT_SECONDS = 30.0


class ConversionError(RuntimeError):
    def __init__(self, reason_code: str, *, retryable: bool) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.retryable = retryable


def validate_pdf_bytes(payload: bytes) -> None:
    if not payload:
        raise ConversionError("conversion_failed", retryable=False)
    if not payload.startswith(PDF_MAGIC):
        raise ConversionError("conversion_failed", retryable=False)


def convert_pdf(path: Path, *, timeout: float = CONVERT_TIMEOUT_SECONDS) -> tuple[str, int]:
    if not path.is_file():
        raise ConversionError("conversion_failed", retryable=False)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_convert, path)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout as exc:
            raise ConversionError("conversion_failed", retryable=True) from exc
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError("conversion_failed", retryable=False) from exc


def _convert(path: Path) -> tuple[str, int]:
    payload = path.read_bytes()
    validate_pdf_bytes(payload)
    from markitdown import MarkItDown

    result = MarkItDown().convert(str(path))
    text = getattr(result, "text_content", "") or ""
    if not str(text).strip():
        raise ConversionError("conversion_failed", retryable=False)
    pages = max(1, str(text).count("\f") or 1)
    return str(text), pages
