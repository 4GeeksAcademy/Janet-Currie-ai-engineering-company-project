"""Print the sanitized guard counts for the current session.

Run from services/api:

    uv run python -m app.agent.guard_summary
"""

from __future__ import annotations

import json

from app.agent.guard_events import summary


def main() -> None:
    print(json.dumps(summary(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
