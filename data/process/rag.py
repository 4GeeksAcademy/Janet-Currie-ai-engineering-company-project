"""Read the approved HealthCore policies, cut them into pieces, and load the search box.

`setup()` is a command you start on purpose. Starting the API does not call it.
"""

from __future__ import annotations

import logging
import math
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger("healthcore.knowledge")

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "docs" / "company-knowledge-base"
COLLECTION_NAME = "healthcore_knowledge"
COMPANY = "healthcore"
LANGUAGE = "en"
QUESTION_MAX_CHARS = 1000
DISTANCE = "cosine"

SOURCE_FILES: tuple[tuple[str, str], ...] = (
    ("healthcore-insurance-coverage.en.md", "insurance-coverage"),
    ("healthcore-appointment-policy.en.md", "appointment-policy"),
    ("healthcore-referral-process.en.md", "referral-process"),
    ("healthcore-new-patient-checklist.en.md", "new-patient-checklist"),
)

REQUIRED_PAYLOAD_FIELDS = (
    "company",
    "source_document",
    "section",
    "language",
    "chunk_index",
    "text",
)

_LIST_LINE = re.compile(r"^(- |\d+\. )")


class KnowledgeError(Exception):
    """Base error. The message is safe to log and is not a secret."""

    category = "knowledge"


class ConfigurationError(KnowledgeError):
    category = "configuration"


class CorpusError(KnowledgeError):
    category = "corpus"


class EmbeddingError(KnowledgeError):
    category = "embedding"


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    embedding_model_id: str
    generation_model_id: str
    qdrant_url: str
    qdrant_api_key: str | None
    collection: str
    k: int
    min_score: float | None
    timeout_seconds: float
    max_output_tokens: int
    log_questions: bool


def normalize_text(value: str) -> str:
    """Trim edges, join indented wrapped lines, and collapse extra spaces."""

    text = value.replace("\r\n", "\n").replace("\r", "\n")
    unwrapped: list[str] = []
    for line in text.split("\n"):
        if unwrapped and line[:1].isspace() and line.strip():
            unwrapped[-1] = f"{unwrapped[-1].rstrip()} {line.strip()}"
        else:
            unwrapped.append(line.strip())
    lines = [" ".join(line.split()) for line in unwrapped]
    cleaned: list[str] = []
    blank = False
    for line in lines:
        if not line:
            if cleaned and not blank:
                cleaned.append("")
            blank = True
            continue
        cleaned.append(line)
        blank = False
    return "\n".join(cleaned).strip()


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def load_settings(*, require_models: bool = False, require_score: bool = False) -> Settings:
    embedding_model_id = os.getenv("EMBEDDING_MODEL_ID", "").strip()
    generation_model_id = os.getenv("GENERATION_MODEL_ID", "").strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    collection = os.getenv("QDRANT_COLLECTION", COLLECTION_NAME).strip() or COLLECTION_NAME
    if collection != COLLECTION_NAME:
        raise ConfigurationError(
            f"QDRANT_COLLECTION must be {COLLECTION_NAME}."
        )

    k_raw = os.getenv("RETRIEVAL_K", "5").strip() or "5"
    try:
        k = int(k_raw)
    except ValueError as exc:
        raise ConfigurationError("RETRIEVAL_K must be a whole number.") from exc
    if k < 1:
        raise ConfigurationError("RETRIEVAL_K must be at least 1.")

    score_raw = os.getenv("RAG_MIN_SCORE", "").strip()
    min_score: float | None
    if not score_raw:
        min_score = None
    else:
        try:
            min_score = float(score_raw)
        except ValueError as exc:
            raise ConfigurationError("RAG_MIN_SCORE must be a number.") from exc
        if not math.isfinite(min_score):
            raise ConfigurationError("RAG_MIN_SCORE must be a finite number.")

    timeout_raw = os.getenv("GENERATION_TIMEOUT_SECONDS", "20").strip() or "20"
    tokens_raw = os.getenv("GENERATION_MAX_TOKENS", "400").strip() or "400"
    try:
        timeout_seconds = float(timeout_raw)
        max_output_tokens = int(tokens_raw)
    except ValueError as exc:
        raise ConfigurationError("Timeout and answer-length settings must be numbers.") from exc
    if timeout_seconds <= 0 or max_output_tokens < 1:
        raise ConfigurationError("Timeout and answer-length settings must be positive.")

    if require_models:
        missing = [
            name
            for name, value in (
                ("LLM_API_KEY", api_key),
                ("LLM_BASE_URL", base_url),
                ("EMBEDDING_MODEL_ID", embedding_model_id),
                ("GENERATION_MODEL_ID", generation_model_id),
            )
            if not value
        ]
        if missing:
            raise ConfigurationError(
                "Missing knowledge settings: " + ", ".join(missing) + "."
            )
        if embedding_model_id == generation_model_id:
            raise ConfigurationError(
                "EMBEDDING_MODEL_ID and GENERATION_MODEL_ID must be different."
            )
    if require_score and min_score is None:
        raise ConfigurationError(
            "RAG_MIN_SCORE is not set. Tune it against the practice questions before searching."
        )

    qdrant_key = os.getenv("QDRANT_API_KEY", "").strip()
    return Settings(
        api_key=api_key,
        base_url=base_url,
        embedding_model_id=embedding_model_id,
        generation_model_id=generation_model_id,
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333").strip()
        or "http://localhost:6333",
        qdrant_api_key=qdrant_key or None,
        collection=collection,
        k=k,
        min_score=min_score,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
        log_questions=_env_flag("RAG_LOG_QUESTIONS"),
    )


def _blocks(text: str) -> list[str]:
    return [normalize_text(part) for part in re.split(r"\n\s*\n", text) if normalize_text(part)]


def _is_heading(block: str) -> bool:
    lines = [line for line in block.split("\n") if line]
    return bool(lines) and all(line.startswith("#") for line in lines)


def _is_list_line(line: str) -> bool:
    return bool(_LIST_LINE.match(line))


def _is_labeled_section(block: str) -> bool:
    lines = [line for line in block.split("\n") if line]
    return bool(lines) and lines[0].endswith(":") and any(_is_list_line(line) for line in lines[1:])


def _is_lead_in(block: str) -> bool:
    lines = [line for line in block.split("\n") if line]
    return bool(lines) and not any(_is_list_line(line) for line in lines) and lines[-1].endswith(":")


def _is_list_block(block: str) -> bool:
    lines = [line for line in block.split("\n") if line]
    # Wrapped list items continue on the next line, so only the first line has the marker.
    return bool(lines) and _is_list_line(lines[0])


def _section_name(block: str) -> str:
    first = block.split("\n", 1)[0].strip().rstrip(":")
    if " (" in first and first.endswith(")"):
        first = first.split(" (", 1)[0]
    named = {
        "No coordinator should confirm coverage for an insurer not listed here": "Unlisted insurers",
        "Automated reminders": "Automated reminders",
        "A patient with 3 no-shows in the last 6 months must be flagged for": "Repeated no-shows",
        "Target completed-referral time": "Current average",
        "If a patient hasn't received appointment options within 5 business days of": "Five business day escalation",
        "Referrals to specialists outside the HealthCore network do not follow this": "External referrals",
        "A new patient who hasn't completed the medical history form before the": "Missing medical history form",
        "When a primary care physician refers a patient to a specialist within the": "Internal referral workflow",
        "Every new patient must complete the following before their first": "Before the first appointment",
        "Documents the patient should bring on the day of the appointment": "Documents to bring",
    }
    for prefix, name in named.items():
        if block.startswith(prefix) or first.startswith(prefix):
            return name
    return first


def chunk_document(text: str, source_document: str, filename: str) -> list[dict]:
    """Cut one policy into pieces that keep a rule and its result together."""

    blocks = _blocks(text)
    pieces: list[tuple[str, str]] = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        if _is_heading(block):
            index += 1
            continue
        if _is_lead_in(block) and index + 1 < len(blocks):
            nxt = blocks[index + 1]
            if _is_list_block(nxt):
                merged = f"{block}\n\n{nxt}"
                pieces.append((_section_name(merged), merged))
                index += 2
                continue
            if _is_labeled_section(nxt):
                follower = index + 1
                while follower < len(blocks) and _is_labeled_section(blocks[follower]):
                    body = f"{block}\n\n{blocks[follower]}"
                    pieces.append((_section_name(blocks[follower]), body))
                    follower += 1
                index = follower
                continue
        pieces.append((_section_name(block), block))
        index += 1

    chunks: list[dict] = []
    for chunk_index, (section, body) in enumerate(pieces):
        payload = {
            "company": COMPANY,
            "source_document": source_document,
            "section": section,
            "language": LANGUAGE,
            "chunk_index": chunk_index,
            "text": body,
            "source_filename": filename,
        }
        chunks.append(payload)
    return chunks


def load_corpus(corpus_dir: Path | None = None) -> list[dict]:
    root = corpus_dir or CORPUS_DIR
    if not root.is_dir():
        raise CorpusError(f"Knowledge folder is missing: {root.name}.")
    chunks: list[dict] = []
    for filename, source_document in SOURCE_FILES:
        path = root / filename
        if not path.is_file():
            raise CorpusError(f"Required knowledge file is missing: {filename}.")
        text = path.read_text(encoding="utf-8")
        if not normalize_text(text):
            raise CorpusError(f"Required knowledge file is empty: {filename}.")
        document_chunks = chunk_document(text, source_document, filename)
        if len(document_chunks) < 3:
            raise CorpusError(
                f"{filename} produced {len(document_chunks)} pieces; at least 3 are required."
            )
        chunks.extend(document_chunks)
    return chunks


def embed(text: str) -> list[float]:
    """Turn one string into one list of numbers, using the embedding model only."""

    cleaned = normalize_text(text)
    if not cleaned:
        raise EmbeddingError("Cannot embed empty text.")
    settings = load_settings(require_models=True)
    try:
        response = httpx.post(
            f"{settings.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": settings.embedding_model_id, "input": cleaned},
            timeout=settings.timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise EmbeddingError("The embedding service timed out.") from exc
    except httpx.HTTPError as exc:
        raise EmbeddingError("The embedding service is unavailable.") from exc
    if response.status_code >= 400:
        raise EmbeddingError("The embedding service rejected the request.")
    try:
        body = response.json()
        vector = body["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise EmbeddingError("The embedding service returned an unusable vector.") from exc
    if not isinstance(vector, list) or not vector:
        raise EmbeddingError("The embedding service returned an empty vector.")
    numbers: list[float] = []
    for item in vector:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise EmbeddingError("The embedding service returned a non-numeric vector.")
        number = float(item)
        if not math.isfinite(number):
            raise EmbeddingError("The embedding service returned a non-finite vector.")
        numbers.append(number)
    return numbers


def _qdrant_client(settings: Settings):
    from qdrant_client import QdrantClient

    kwargs: dict = {"url": settings.qdrant_url, "timeout": int(settings.timeout_seconds)}
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key
    return QdrantClient(**kwargs)


def setup(*, client=None, embed_fn=None, corpus_dir: Path | None = None) -> dict:
    """Delete and reload the whole approved set. A second run does not add duplicates."""

    chunks = load_corpus(corpus_dir)
    vector_fn = embed_fn or embed
    vectors = [vector_fn(chunk["text"]) for chunk in chunks]
    size = len(vectors[0])
    if any(len(vector) != size for vector in vectors):
        raise EmbeddingError("Embedding vectors do not share one length.")

    settings = load_settings()
    search = client or _qdrant_client(settings)
    from qdrant_client.models import Distance, PointStruct, VectorParams

    points = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{COMPANY}:{chunk['source_document']}:{chunk['section']}:{chunk['chunk_index']}",
            )
        )
        points.append(PointStruct(id=point_id, vector=vector, payload=chunk))
    try:
        if search.collection_exists(settings.collection):
            search.delete_collection(settings.collection)
        search.create_collection(
            collection_name=settings.collection,
            vectors_config=VectorParams(size=size, distance=Distance.COSINE),
        )
        search.upsert(collection_name=settings.collection, points=points)
    except Exception as exc:
        if client is not None:
            raise
        raise KnowledgeError("The search database is unavailable.") from exc

    per_document: dict[str, int] = {}
    for chunk in chunks:
        key = chunk["source_document"]
        per_document[key] = per_document.get(key, 0) + 1
    summary = {
        "collection": settings.collection,
        "document_count": len(SOURCE_FILES),
        "chunk_count": len(chunks),
        "chunks_per_document": per_document,
        "vector_size": size,
        "distance": DISTANCE,
    }
    logger.info(
        "knowledge_setup collection=%s documents=%s chunks=%s vector_size=%s distance=%s",
        summary["collection"],
        summary["document_count"],
        summary["chunk_count"],
        summary["vector_size"],
        summary["distance"],
    )
    return summary


if __name__ == "__main__":
    import json

    print(json.dumps(setup(), indent=2))
