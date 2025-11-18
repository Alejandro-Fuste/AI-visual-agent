from __future__ import annotations

"""Agent package for the visual desktop assistant."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
