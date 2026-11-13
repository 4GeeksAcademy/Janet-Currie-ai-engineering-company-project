# Agent memory evidence

These cycles are the deterministic tests in `services/api/tests/test_agent_memory.py`. They use a fake writing model. A live model was not called.

No patient identifier is copied here. The blocked case is described only by the reason code `phi_detected`.

## Cycle A: approved and recalled

1. A signed-in staff member submits the Manchester referral correction.
2. The answer includes the normal operational reply and the exact pending sentence, with the words "I have not saved this yet."
3. The next message on the same `conversation_id` is `Yes, save it`.
4. The audit row moves to `approved` and one active memory row is stored. The response says it was saved.
5. A later question about Manchester referrals is answered with that approved sentence.
6. The bearer token is not in the memory row.

## Cycle B: rejected and unchanged

1. The same staff member submits the Monday-morning referral pattern.
2. A pending proposal is shown.
3. The next message is `No, do not save`.
4. The audit row is `rejected`. No active memory is added.
5. A later question about Monday mornings does not repeat the rejected sentence.

## Blocked case

A model candidate that names a patient is refused before it is shown. The response uses the fixed HealthCore privacy sentence. The audit row is `blocked` with reason `phi_detected` and empty content. The test asserts the patient placeholder is absent from the response, the row, and the log line.
