"""Ephemeral history for browser tests; never use a user's real history database."""

import os
import sys
import tempfile
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="iea-e2e-") as directory:
        os.environ["IEA_HISTORY"] = "true"
        os.environ["IEA_HISTORY_PATH"] = str(Path(directory) / "history.sqlite3")
        uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000)
