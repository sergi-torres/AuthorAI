"""Ensure the backend package root is importable when running pytest from here.

pytest inserts the directory containing the rootdir conftest.py onto sys.path,
so tests can `from app.main import app` without an editable install.

The monorepo's ``ai_pipeline`` is added the same way, and for the same reason
the production code does it (``app.routes.generate._ensure_ai_pipeline_on_path``):
CI installs only ``backend/``, so ``import autoria_ai`` fails there while
passing locally, where an editable install papers over the difference. Tests
that assert on pipeline constants must not be green locally and red in CI.
"""

import sys
from pathlib import Path

_AI_PIPELINE = Path(__file__).resolve().parent.parent / "ai_pipeline"
if _AI_PIPELINE.is_dir() and str(_AI_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_AI_PIPELINE))
