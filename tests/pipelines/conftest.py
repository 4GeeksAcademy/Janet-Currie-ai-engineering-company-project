"""Put data/ and this test folder on sys.path."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
THIS_DIR = Path(__file__).resolve().parent
for _path in (DATA_DIR, THIS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
