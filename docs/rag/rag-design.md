# HealthCore knowledge helper

A signed-in coordinator asks one policy question. The staff app shows only the written answer.

## Flow

1. Four approved English files live in `docs/company-knowledge-base/`.
2. `setup()` in `data/process/rag.py` reads them, cuts them into pieces, embeds each piece, and loads Qdrant.
3. The collection name is `healthcore_knowledge`.
4. `retrieve()` in `data/pipelines/rag.py` embeds the question with the same `embed()` function, asks Qdrant for at most `k` neighbors, and drops anything below the minimum score.
5. `generate_answer()` builds a prompt from the question and those passages, then calls the writing model.
6. `query()` only calls `retrieve()` and then `generate_answer()`.
7. `POST /knowledge/query` calls `query()` and returns `{ "answer": "..." }`.
8. The staff page at `/knowledge` shows that answer.

A later agent can call `retrieve()` and `generate_answer()` separately. Starting the API does not rebuild the collection.

## Collection and payload

- Collection: `healthcore_knowledge`
- Distance: cosine. Qdrant's cosine score is higher when the texts are closer. A score equal to the minimum is kept.
- Vector size: not measured yet. `setup()` uses the length of the first real embedding. It does not guess a number.
- Every point stores `company` (`healthcore`), `source_document`, `section`, `language` (`en`), `chunk_index`, and `text`. The filename is stored as extra `source_filename`.

`source_document` is one of `insurance-coverage`, `appointment-policy`, `referral-process`, or `new-patient-checklist`.

## Chunking

The files are short and use labels, bullets, and numbered steps rather than many headings. The cutter:

- Drops the title line.
- Joins an indented wrapped line to the line above, so a rule is not split by the file's line wrap.
- Keeps a label and its bullets together.
- Keeps a lead-in sentence with the numbered steps that follow it.
- Copies the insurance introduction onto both the United States piece and the United Kingdom piece, because that sentence says coverage depends on the country.
- Leaves a later prose rule as its own piece.

There is no extra overlap beyond that one insurance introduction. A second copy of a long passage would crowd the top results with near-duplicates.

Counted from the four files on 2026-11-07:

| Document | Pieces | Sections |
| --- | ---: | --- |
| insurance-coverage | 3 | United States (437 characters), United Kingdom (507), Unlisted insurers (131) |
| appointment-policy | 4 | Booking appointments (211), Cancellation policy (313), Automated reminders (186), Repeated no-shows (167) |
| referral-process | 4 | Internal referral workflow (547), Current average (198), Five business day escalation (200), External referrals (157) |
| new-patient-checklist | 3 | Before the first appointment (512), Documents to bring (195), Missing medical history form (208) |

Total: 14 pieces. Each document has at least three.

The cancellation fee, the 24-hour timing, the currencies, and the Medicare/Medicaid exemption stay in Cancellation policy. Georgia stays with Medicaid. The five-business-day rule stays with Marcus Reid. The 11-day sentence stays with the warning that it is not a published service commitment. HIPAA and UK GDPR stay in the new-patient checklist.

Exactly 24 hours is not given a fee. The source says more than 24 hours is free and less than 24 hours is charged. The helper must not invent the equal-to-24-hours case.

## Models

`EMBEDDING_MODEL_ID` and `GENERATION_MODEL_ID` are read from the environment. They must be different. No student model id was available in this workspace, so both names are still blank. Do not fill them in until the 4Geeks access page is checked.

`embed()` calls `{LLM_BASE_URL}/embeddings`. `generate_answer()` calls `{LLM_BASE_URL}/chat/completions`. `LLM_BASE_URL` should include `/v1` when the provider uses that prefix. Calls time out. They are not retried.

## Retrieval settings

- `RETRIEVAL_K` defaults to 5.
- `RAG_MIN_SCORE` is required before `query()` will run. It is not set, because it has not been tuned on real embeddings.
- A question with no passage at or above the score still calls the writing model with an empty list. The prompt tells it to say the knowledge base does not contain enough relevant information.
- If Qdrant is down, the API returns "The knowledge search is unavailable. Please try again."
- If the writing or embedding service is down, the API returns "The answer service is unavailable. Please try again."
- Those two failures are different from the honest "not enough information" answer, which is a normal success response.

## Reload rule

`setup()` deletes `healthcore_knowledge` if it exists, creates it again, and loads the full approved set. A second run replaces the pieces. It does not add a second copy. Point ids are stable hashes of the source, section, and chunk index, but the delete is what prevents duplicates.

## Privacy

The corpus is policy text only. Tests, practice questions, and examples do not contain patient names, birth dates, record numbers, or made-up patient stories.

Logs may include a request id, durations, hit count, whether zero passages matched, source-document names, and an error category. They do not include the question, the prompt, the answer, the number lists, or any key unless `RAG_LOG_QUESTIONS` is explicitly turned on for local debugging. That switch is off by default.

The browser cannot choose the model, the collection, the score line, or the hidden instructions. Questions longer than 1000 characters are rejected.

## Recall@3

Practice questions are in `data/eval/test-queries.json`: nine in-domain questions covering all four documents, plus one off-topic question that must not match. The off-topic question is not part of the percentage.

For each in-domain question, success means the expected section is in the top three. The score is successes divided by nine. The target is at least 80%.

The scorer was checked with fake results (7 of 8 = 0.875, with the off-topic question ignored). The live score was not run. `data/eval/recall_at_3.py` stopped because `LLM_API_KEY`, `LLM_BASE_URL`, `EMBEDDING_MODEL_ID`, and `GENERATION_MODEL_ID` are empty. No vector size, minimum score, or live Recall@3 number exists yet.

`data/eval/evaluation_report.md` and `data/eval/sales_forecast/` were not changed.

## Commands

```bash
# Pipeline tests from the repo root, using the API environment.
services/api/.venv/bin/python -m pytest tests/pipelines/test_rag.py

# Same file through uv.
uv --directory services/api run pytest ../../tests/pipelines/test_rag.py

# API tests, including the knowledge route.
uv --directory services/api run pytest

# Staff tests and types.
npm test -w uis/web -- src/components/__tests__/KnowledgeAssistant.test.tsx
npm run typecheck -w uis/web

# Compose file, including Qdrant.
docker compose config

# After the model settings and RAG_MIN_SCORE are filled in, and Qdrant is up:
uv --directory services/api run python ../../data/process/rag.py
uv --directory services/api run python ../../data/eval/recall_at_3.py
```

Inside Compose, the API uses `QDRANT_URL=http://qdrant:6333`. On the host, the default is `http://localhost:6333`.

## Limits

- No chat memory.
- No document upload.
- No medical advice.
- The live embedding model, vector size, minimum score, and Recall@3 result are still unknown.
- Qdrant was added to Compose and `docker compose config` succeeded. A live index was not created, because the model settings are empty.
