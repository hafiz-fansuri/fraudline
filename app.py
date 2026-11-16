"""Vercel serves the same FastAPI application and verified synthetic model."""

import ctypes
import os
from pathlib import Path

if os.environ.get("VERCEL"):
    ctypes.CDLL(str(Path(__file__).parent / "native/libgomp.so.1"), mode=ctypes.RTLD_GLOBAL)
    os.environ.setdefault("FRAUDLINE_HOME", str(Path(__file__).parent))
    os.environ.setdefault("FRAUDLINE_ARTIFACTS", str(Path(__file__).parent / "demo-bundle"))
    # Vercel's source bundle is read-only; audit records are instance-local demo storage.
    os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/fraudline/events.db")

from fraudline.api import app as app  # noqa: E402
