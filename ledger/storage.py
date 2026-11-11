"""SQLite journal. Events are accepted independently of causal arrival order."""
import sqlite3
from pathlib import Path
from .model import Event, ConflictError

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
 tenant TEXT NOT NULL, provider TEXT NOT NULL, event_id TEXT NOT NULL,
 payment_id TEXT NOT NULL, kind TEXT NOT NULL, amount INTEGER NOT NULL,
 currency TEXT NOT NULL, parent_id TEXT,
 PRIMARY KEY (tenant, provider, event_id)
);
CREATE INDEX IF NOT EXISTS payment_events ON events(tenant, provider, payment_id);
CREATE TABLE IF NOT EXISTS batches (
 batch_id INTEGER PRIMARY KEY AUTOINCREMENT, inserted INTEGER NOT NULL,
 duplicates INTEGER NOT NULL
);
"""

class Store:
    def __init__(self, path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def append(self, events):
        inserted = duplicates = 0
        with self.db:
            for event in events:
                found = self.db.execute("SELECT * FROM events WHERE tenant=? AND provider=? AND event_id=?", event.key).fetchone()
                if found:
                    if Event(**dict(found)).canonical() != event.canonical():
                        raise ConflictError("event identity reused with different content")
                    duplicates += 1
                    continue
                self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", tuple(event.payload().values()))
                inserted += 1
            self.db.execute("INSERT INTO batches(inserted,duplicates) VALUES (?,?)", (inserted, duplicates))
        return {"inserted": inserted, "duplicates": duplicates}

    def read(self, tenant):
        return [dict(row) for row in self.db.execute("SELECT * FROM events WHERE tenant=? ORDER BY provider,event_id", (tenant,))]

    def history(self):
        return [dict(row) for row in self.db.execute("SELECT * FROM batches ORDER BY batch_id")]

    def close(self):
        self.db.close()
