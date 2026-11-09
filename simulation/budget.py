"""B12 process-shared cost accounting and outstanding-request reservations."""

import sqlite3
import time
import os
from pathlib import Path


class StudyHalt(RuntimeError):
    pass


class SharedBudget:
    def __init__(self, path, limit=90.0):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.limit = limit
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, cost REAL, reserved REAL NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS control (key TEXT PRIMARY KEY, value TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS workers (id TEXT PRIMARY KEY, pid INTEGER, started REAL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=60)

    def check(self):
        with self.connect() as db:
            row = db.execute("SELECT value FROM control WHERE key='halt'").fetchone()
        if row:
            raise StudyHalt(row[0])

    def halt(self, reason):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO control VALUES ('halt', ?)", (reason,))

    def totals(self):
        with self.connect() as db:
            return db.execute("SELECT COALESCE(SUM(cost),0), COALESCE(SUM(reserved),0) FROM calls").fetchone()

    def reserve(self, call_id, amount):
        self.check()
        blocked = False
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            spent, pending = db.execute("SELECT COALESCE(SUM(cost),0), COALESCE(SUM(reserved),0) FROM calls").fetchone()
            if spent + pending + amount > self.limit:
                db.execute("INSERT OR REPLACE INTO control VALUES ('halt', 'Code-level spending guard reached')")
                blocked = True
            else:
                db.execute("INSERT INTO calls VALUES (?, NULL, ?)", (call_id, amount))
        if blocked:
            raise StudyHalt("Code-level spending guard reached")

    def settle(self, call_id, cost):
        if cost is None or cost < 0:
            self.halt("Actual call cost is missing or invalid")
            raise StudyHalt("Actual call cost is missing or invalid")
        with self.connect() as db:
            db.execute("UPDATE calls SET cost=?, reserved=0 WHERE id=?", (cost, call_id))
            spent = db.execute("SELECT COALESCE(SUM(cost),0) FROM calls").fetchone()[0]
            if spent >= self.limit:
                db.execute("INSERT OR REPLACE INTO control VALUES ('halt', 'Code-level spending guard reached')")

    def release_unbilled(self, call_id):
        with self.connect() as db:
            db.execute("DELETE FROM calls WHERE id=? AND cost IS NULL", (call_id,))

    def capacity_limit(self, reduce=False):
        with self.connect() as db:
            if reduce:
                row = db.execute("SELECT value FROM control WHERE key='parallel_seed_limit'").fetchone()
                limit = max(1, int(row[0]) // 2) if row else 2
                db.execute("INSERT OR REPLACE INTO control VALUES ('parallel_seed_limit', ?)", (str(limit),))
                return limit
            row = db.execute("SELECT value FROM control WHERE key='parallel_seed_limit'").fetchone()
            return int(row[0]) if row else None

    def register(self, worker):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO workers VALUES (?, ?, ?)", (worker, os.getpid(), time.time()))

    def unregister(self, worker):
        with self.connect() as db:
            db.execute("DELETE FROM workers WHERE id=?", (worker,))

    def wait_for_turn(self, worker):
        while True:
            self.check()
            limit = self.capacity_limit()
            if limit is None:
                return
            with self.connect() as db:
                rows = db.execute("SELECT id,pid FROM workers ORDER BY started,id").fetchall()
                live = []
                for identity, pid in rows:
                    try:
                        os.kill(pid, 0)
                        live.append(identity)
                    except ProcessLookupError:
                        db.execute("DELETE FROM workers WHERE id=?", (identity,))
            if worker in live[:limit]:
                return
            time.sleep(1)
