"""Score Recall@3 for the knowledge helper.

This talks to the configured embedding model and Qdrant. It does not invent a score
when those services are not configured.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

from pipelines.rag import score_recall_at_3  # noqa: E402
from process.rag import ConfigurationError, load_settings  # noqa: E402

QUERIES = Path(__file__).with_name("test-queries.json")


def main() -> int:
    try:
        settings = load_settings(require_models=True, require_score=True)
    except ConfigurationError as exc:
        print(f"Recall@3 was not run: {exc}")
        return 2

    from pipelines.rag import retrieve

    cases = json.loads(QUERIES.read_text(encoding="utf-8"))
    hits_by_id: dict[str, list[dict]] = {}
    no_match_failures: list[str] = []
    for case in cases:
        hits = retrieve(case["question"], k=3, min_score=settings.min_score)
        hits_by_id[case["id"]] = hits
        if case.get("expect_no_match") and hits:
            no_match_failures.append(case["id"])
    score = score_recall_at_3(cases, hits_by_id)
    report = {
        "embedding_model_id": settings.embedding_model_id,
        "generation_model_id": settings.generation_model_id,
        "collection": settings.collection,
        "min_score": settings.min_score,
        "k": 3,
        **score,
        "out_of_domain_failures": no_match_failures,
    }
    print(json.dumps(report, indent=2))
    if score["recall_at_3"] < 0.8 or no_match_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
