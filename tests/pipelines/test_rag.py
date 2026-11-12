"""Knowledge helper tests. They use fakes, so they do not need Qdrant or a model key."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from process import rag as prep
from pipelines import rag

PAYLOAD = {
    "company": "healthcore",
    "source_document": "appointment-policy",
    "section": "Cancellation policy",
    "language": "en",
    "chunk_index": 1,
    "text": "Cancelling less than 24 hours in advance costs 50 USD for private-pay patients.",
}


def _point(score: float, payload: dict | None):
    return type("Point", (), {"score": score, "payload": payload})()


def _result(points: list):
    return type("Result", (), {"points": points})()


def _model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://models.example/v1")
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "embed-test")
    monkeypatch.setenv("GENERATION_MODEL_ID", "write-test")
    monkeypatch.setenv("RAG_MIN_SCORE", "0.5")


def test_each_document_has_at_least_three_chunks() -> None:
    chunks = prep.load_corpus()
    counts: dict[str, int] = {}
    for chunk in chunks:
        for field in prep.REQUIRED_PAYLOAD_FIELDS:
            assert field in chunk
        assert chunk["company"] == "healthcore"
        assert chunk["language"] == "en"
        counts[chunk["source_document"]] = counts.get(chunk["source_document"], 0) + 1
    assert set(counts) == {
        "insurance-coverage",
        "appointment-policy",
        "referral-process",
        "new-patient-checklist",
    }
    assert all(count >= 3 for count in counts.values())


def test_sensitive_rules_stay_together() -> None:
    chunks = prep.load_corpus()

    def joined(source: str, section: str) -> str:
        return "\n".join(
            chunk["text"]
            for chunk in chunks
            if chunk["source_document"] == source and chunk["section"] == section
        )

    united_states = joined("insurance-coverage", "United States")
    assert "Medicaid" in united_states and "Georgia" in united_states
    cancellation = joined("appointment-policy", "Cancellation policy")
    assert "50 USD" in cancellation and "Medicare or Medicaid" in cancellation
    escalation = joined("referral-process", "Five business day escalation")
    assert "5 business days" in escalation and "Marcus Reid" in escalation
    average = joined("referral-process", "Current average")
    assert "11 days" in average and "not a published service commitment" in average
    checklist = joined("new-patient-checklist", "Before the first appointment")
    assert "HIPAA" in checklist and "UK GDPR" in checklist


def test_missing_document_stops_before_a_partial_index(tmp_path: Path) -> None:
    with pytest.raises(prep.CorpusError, match="missing"):
        prep.load_corpus(tmp_path)


def test_setup_reloads_without_growing(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSearch:
        def __init__(self) -> None:
            self.exists = False
            self.deleted = 0
            self.sizes: list[int] = []
            self.upserts: list[int] = []

        def collection_exists(self, _name: str) -> bool:
            return self.exists

        def delete_collection(self, _name: str) -> None:
            self.deleted += 1
            self.exists = False

        def create_collection(self, collection_name: str, vectors_config) -> None:
            assert collection_name == "healthcore_knowledge"
            self.sizes.append(vectors_config.size)
            self.exists = True

        def upsert(self, collection_name: str, points) -> None:
            assert collection_name == "healthcore_knowledge"
            self.upserts.append(len(points))

    search = FakeSearch()
    first = prep.setup(client=search, embed_fn=lambda _text: [0.2, 0.4, 0.6])
    second = prep.setup(client=search, embed_fn=lambda _text: [0.2, 0.4, 0.6])
    assert first["chunk_count"] == second["chunk_count"]
    assert search.upserts[0] == search.upserts[1]
    assert search.deleted == 1
    assert search.sizes == [3, 3]
    assert first["distance"] == "cosine"
    assert first["vector_size"] == 3


def test_embed_rejects_blank_before_the_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def explode(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("provider was called")

    monkeypatch.setattr(httpx, "post", explode)
    with pytest.raises(prep.EmbeddingError, match="empty"):
        prep.embed("   \n")
    assert called is False


def test_embed_checks_shape_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    _model_env(monkeypatch)
    seen: dict = {}

    class Response:
        status_code = 200

        def json(self) -> dict:
            return {"data": [{"embedding": [1.0, 2.5]}]}

    def post(url, headers, json, timeout):
        seen["url"] = url
        seen["json"] = json
        seen["timeout"] = timeout
        assert headers["Authorization"] == "Bearer test-key"
        return Response()

    monkeypatch.setattr(httpx, "post", post)
    assert prep.embed("  Georgia Medicaid  ") == [1.0, 2.5]
    assert seen["json"]["model"] == "embed-test"
    assert seen["json"]["input"] == "Georgia Medicaid"
    assert seen["url"] == "https://models.example/v1/embeddings"

    class Bad:
        status_code = 200

        def json(self) -> dict:
            return {"data": [{"embedding": [1.0, float("nan")]}]}

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Bad())
    with pytest.raises(prep.EmbeddingError, match="non-finite"):
        prep.embed("Medicaid")


def test_same_model_id_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _model_env(monkeypatch)
    monkeypatch.setenv("GENERATION_MODEL_ID", "embed-test")
    with pytest.raises(prep.ConfigurationError, match="different"):
        prep.embed("Medicaid")


def test_retrieve_filters_orders_and_rejects_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_embed(text: str) -> list[float]:
        captured["embedded"] = text
        return [0.1, 0.2]

    def fake_client(_settings):
        class Client:
            def query_points(self, **kwargs):
                captured["search"] = kwargs
                return _result(
                    [
                        _point(0.9, {**PAYLOAD, "text": "highest"}),
                        _point(0.5, {**PAYLOAD, "text": "boundary"}),
                        _point(0.49, {**PAYLOAD, "text": "below"}),
                    ]
                )

        return Client()

    monkeypatch.setattr(prep, "embed", fake_embed)
    monkeypatch.setattr(prep, "_qdrant_client", fake_client)
    found = rag.retrieve("cancellation fee", k=5, min_score=0.5)
    assert captured["embedded"] == "cancellation fee"
    assert captured["search"]["query"] == [0.1, 0.2]
    assert captured["search"]["limit"] == 5
    assert [item["text"] for item in found] == ["highest", "boundary"]
    assert all(type(item) is dict for item in found)
    assert "score" not in found[0]

    def none_client(_settings):
        class Client:
            def query_points(self, **kwargs):
                return _result([_point(0.1, PAYLOAD)])

        return Client()

    monkeypatch.setattr(prep, "_qdrant_client", none_client)
    assert rag.retrieve("cancellation fee", k=5, min_score=0.5) == []

    def two_client(_settings):
        class Client:
            def query_points(self, **kwargs):
                return _result([_point(0.8, PAYLOAD), _point(0.7, {**PAYLOAD, "text": "second"})])

        return Client()

    monkeypatch.setattr(prep, "_qdrant_client", two_client)
    assert len(rag.retrieve("cancellation fee", k=5, min_score=0.2)) == 2

    def called_embed(_text: str) -> list[float]:
        raise AssertionError("empty questions must not be embedded")

    monkeypatch.setattr(prep, "embed", called_embed)
    with pytest.raises(rag.EmptyQueryError):
        rag.retrieve("   ", k=5, min_score=0.5)


def test_retrieve_rejects_a_broken_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prep, "embed", lambda _text: [0.1])

    def fake_client(_settings):
        class Client:
            def query_points(self, **kwargs):
                return _result([_point(0.9, {"text": "missing the other fields"})])

        return Client()

    monkeypatch.setattr(prep, "_qdrant_client", fake_client)
    with pytest.raises(rag.RetrievalError, match="required fields"):
        rag.retrieve("fee", k=5, min_score=0.2)


def test_query_returns_the_written_answer_not_the_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    _model_env(monkeypatch)
    seen: dict = {}

    def fake_retrieve(question: str, *, k: int, min_score: float) -> list[dict]:
        seen["question"] = question
        seen["k"] = k
        seen["min_score"] = min_score
        return [PAYLOAD]

    def fake_generate(question: str, context: list[dict]) -> str:
        seen["context"] = context
        return "A private-pay cancellation inside 24 hours can cost 50 USD."

    monkeypatch.setattr(rag, "retrieve", fake_retrieve)
    monkeypatch.setattr(rag, "generate_answer", fake_generate)
    answer = rag.query("Is there a charge for cancelling 12 hours in advance?")
    assert answer == "A private-pay cancellation inside 24 hours can cost 50 USD."
    assert PAYLOAD["text"] not in answer
    assert seen["context"] == [PAYLOAD]
    assert seen["k"] == 5
    assert seen["min_score"] == 0.5


def test_empty_retrieval_still_calls_the_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    _model_env(monkeypatch)
    monkeypatch.setattr(rag, "retrieve", lambda *args, **kwargs: [])

    def fake_generate(question: str, context: list[dict]) -> str:
        assert context == []
        return "The HealthCore knowledge base does not contain enough relevant information."

    monkeypatch.setattr(rag, "generate_answer", fake_generate)
    answer = rag.query("What is the capital of France?")
    assert "does not contain enough" in answer


def test_generation_failure_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    _model_env(monkeypatch)
    monkeypatch.setattr(rag, "retrieve", lambda *args, **kwargs: [PAYLOAD])

    def explode(question: str, context: list[dict]) -> str:
        raise rag.GenerationUnavailableError("The answer service is unavailable.")

    monkeypatch.setattr(rag, "generate_answer", explode)
    with pytest.raises(rag.GenerationUnavailableError):
        rag.query("Is there a fee?")


def test_prompt_contains_the_question_context_and_grounding_rules() -> None:
    system, user = rag.build_prompt("Do Georgia clinics accept Medicaid?", [PAYLOAD])
    assert "Do Georgia clinics accept Medicaid?" in user
    assert PAYLOAD["text"] in user
    assert "do not invent" in system.lower()
    assert "other policy" not in user
    empty_system, empty_user = rag.build_prompt("What is the capital of France?", [])
    assert "Reference passages: none." in empty_user
    assert "does not contain enough relevant information" in empty_system


def test_generation_normalizes_the_provider_text(monkeypatch: pytest.MonkeyPatch) -> None:
    _model_env(monkeypatch)

    class Response:
        status_code = 200

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "  Kind answer.  "}}]}

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Response())
    assert rag.generate_answer("Any fee?", [PAYLOAD]) == "Kind answer."

    class Empty:
        status_code = 200

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "  "}}]}

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Empty())
    with pytest.raises(rag.GenerationUnavailableError, match="empty"):
        rag.generate_answer("Any fee?", [PAYLOAD])


def test_recall_math_clears_eighty_percent() -> None:
    cases = [
        {
            "id": f"q{index}",
            "in_domain": True,
            "expected_source_document": "insurance-coverage",
            "expected_section": "United States",
        }
        for index in range(8)
    ]
    cases.append({"id": "weather", "in_domain": False, "expect_no_match": True})
    hits = {f"q{index}": [{"source_document": "insurance-coverage", "section": "United States"}] for index in range(8)}
    hits["q7"] = [{"source_document": "appointment-policy", "section": "Booking appointments"}]
    hits["weather"] = [{"source_document": "insurance-coverage", "section": "United States"}]
    score = rag.score_recall_at_3(cases, hits)
    assert score["evaluated"] == 8
    assert score["successes"] == 7
    assert score["recall_at_3"] == 0.875
    assert score["failures"] == ["q7"]
