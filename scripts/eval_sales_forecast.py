#!/usr/bin/env python3
"""Evaluate the frozen HealthCore sales forecast on training-year folds."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = Path(__file__).resolve().parent / "sales_forecast"
VENV_PY = PKG_ROOT / ".venv" / "bin" / "python"


def _ensure_venv() -> None:
    if Path(sys.executable).resolve() == VENV_PY.resolve():
        return
    if not VENV_PY.exists():
        sys.stderr.write(
            "Sales-forecast venv missing. From the repo root run:\n"
            "  uv sync --directory scripts/sales_forecast --group dev\n"
        )
        raise SystemExit(1)
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])


def main() -> int:
    _ensure_venv()
    if str(PKG_ROOT) not in sys.path:
        sys.path.insert(0, str(PKG_ROOT))
    from sales_forecast.evaluation import run_evaluation

    run_evaluation(REPO_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
