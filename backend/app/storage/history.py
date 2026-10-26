import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime


class History:
    def __init__(self, settings):
        self.enabled = settings.history
        self.path = settings.history_path
        self.lock = threading.RLock()
        if self.enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.connect() as db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, created TEXT, filename TEXT, sha256 TEXT, result TEXT)"
                )

    def connect(self):
        if not self.enabled:
            raise ValueError("History is disabled. Set IEA_HISTORY=true and restart to opt in.")
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA secure_delete=ON")
        return db

    def add(self, result):
        record_id = uuid.uuid4().hex
        result = {**result, "history_id": record_id}
        with self.lock, self.connect() as db:
            db.execute(
                "INSERT INTO analyses VALUES (?,?,?,?,?)",
                (
                    record_id,
                    datetime.now(UTC).isoformat(),
                    result["image"]["filename"],
                    result["image"]["sha256"],
                    json.dumps(result, allow_nan=False),
                ),
            )
        return result

    def list(self):
        if not self.enabled:
            return []
        with self.connect() as db:
            rows = db.execute(
                "SELECT id,created,filename,sha256 FROM analyses ORDER BY created DESC LIMIT 200"
            ).fetchall()
        return [dict(zip(["id", "created", "filename", "sha256"], r, strict=True)) for r in rows]

    def get(self, record_id):
        with self.connect() as db:
            row = db.execute("SELECT result FROM analyses WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise KeyError("History record unavailable.")
        return json.loads(row[0])

    def delete(self, record_id=None):
        with self.lock, self.connect() as db:
            if record_id:
                db.execute("DELETE FROM analyses WHERE id=?", (record_id,))
            else:
                db.execute("DELETE FROM analyses")
            # Remove deleted result text from reusable pages; no images are retained.
            db.execute("PRAGMA secure_delete=ON")
