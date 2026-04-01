"""Vercel serverless function entry point for India Cashflow OS API.

This file is the handler for Vercel's Python runtime.
It imports the FastAPI app and exposes it as the ASGI handler.
"""
from pathlib import Path
import sys

# Ensure src/ is on the Python path for module imports
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR / "apps" / "api" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cashflow_os.api.main import app  # noqa: E402

handler = app
