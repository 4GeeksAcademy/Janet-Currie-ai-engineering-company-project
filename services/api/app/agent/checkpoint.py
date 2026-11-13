"""Keep a full checkpoint in this process and a safe copy on disk.

Later nodes in the same turn still read the question. The SQLite file keeps only
status, route, tool outcome, incident id, and source names.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

DURABLE_KEYS = frozenset({"status", "route", "tool_outcome", "incident_id", "sources_used"})


class DurableSafeSaver(BaseCheckpointSaver):
    def __init__(self, inner: Any) -> None:
        super().__init__(serde=getattr(inner, "serde", None))
        self.inner = inner
        self._live: dict[tuple[str, str], dict] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def get_tuple(self, config: dict) -> CheckpointTuple | None:
        saved = self.inner.get_tuple(config)
        if saved is None:
            return None
        checkpoint_id = saved.checkpoint.get("id")
        full = self._live.get((self._thread_id(config), str(checkpoint_id)))
        if full is None:
            return saved
        checkpoint = dict(saved.checkpoint)
        checkpoint["channel_values"] = full
        return saved._replace(checkpoint=checkpoint)

    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict,
    ) -> dict:
        values = dict(checkpoint.get("channel_values") or {})
        checkpoint_id = str(checkpoint.get("id"))
        self._live[(self._thread_id(config), checkpoint_id)] = values
        stripped = dict(checkpoint)
        stripped["channel_values"] = {key: values[key] for key in DURABLE_KEYS if key in values}
        safe_metadata = _strip_metadata(metadata)
        return self.inner.put(config, stripped, safe_metadata, new_versions)

    def put_writes(self, config: dict, writes, task_id: str, task_path: str = "") -> None:
        durable = [item for item in writes if item and item[0] in DURABLE_KEYS]
        if not durable:
            return
        self.inner.put_writes(config, durable, task_id, task_path)

    @staticmethod
    def _thread_id(config: dict) -> str:
        return str(config.get("configurable", {}).get("thread_id", ""))


def _strip_metadata(metadata: CheckpointMetadata) -> CheckpointMetadata:
    if not isinstance(metadata, dict):
        return metadata
    cleaned = dict(metadata)
    for key in ("writes", "source_input", "question", "answer"):
        cleaned.pop(key, None)
    return cleaned
