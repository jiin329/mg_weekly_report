"""SQLite-based persistent storage for rooms and messages (task 4.2).

Uses Python's built-in sqlite3 module — no extra dependencies.
Data survives across application restarts (Requirement 3.4, 8.4).
The DB file path is configurable for Phase 1 (project-local) and
Phase 2 (%APPDATA% or equivalent).
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional


class Repository:
    """Persistent storage layer for ChatRooms and Messages."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        # check_same_thread=False: FastAPI serves sync endpoints from a thread
        # pool, so the connection is accessed from threads other than the one
        # that created it. SQLite's default serialized threading mode guards the
        # connection with an internal mutex, which is sufficient for this local,
        # single-user desktop app.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                closed_at TEXT,
                report TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_room_time
                ON messages(room_id, created_at);
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Room operations
    # ------------------------------------------------------------------

    def create_room(self) -> dict:
        """Create a new active room and return its dict representation."""
        room_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO rooms (id, status, created_at) VALUES (?, 'active', ?)",
            (room_id, created_at),
        )
        self._conn.commit()
        return {
            "id": room_id,
            "status": "active",
            "created_at": created_at,
            "closed_at": None,
            "report": None,
        }

    def get_room(self, room_id: str) -> Optional[dict]:
        """Get a room by id. Returns None if not found."""
        cur = self._conn.execute(
            "SELECT id, status, created_at, closed_at, report FROM rooms WHERE id = ?",
            (room_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_room(row)

    def list_rooms(self) -> list[dict]:
        """List all rooms ordered by creation time (newest first)."""
        cur = self._conn.execute(
            "SELECT id, status, created_at, closed_at, report FROM rooms ORDER BY created_at DESC"
        )
        return [self._row_to_room(row) for row in cur.fetchall()]

    def close_room(self, room_id: str, *, closed_at: str, report: dict) -> None:
        """Mark a room as closed with the given report."""
        self._conn.execute(
            "UPDATE rooms SET status = 'closed', closed_at = ?, report = ? WHERE id = ?",
            (closed_at, json.dumps(report), room_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Message operations
    # ------------------------------------------------------------------

    def add_message(
        self,
        *,
        id: str,
        room_id: str,
        sender: str,
        content: str,
        created_at: str,
    ) -> dict:
        """Store a message and return its dict representation."""
        self._conn.execute(
            "INSERT INTO messages (id, room_id, sender, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (id, room_id, sender, content, created_at),
        )
        self._conn.commit()
        return {
            "id": id,
            "room_id": room_id,
            "sender": sender,
            "content": content,
            "created_at": created_at,
        }

    def get_messages(self, room_id: str) -> list[dict]:
        """Get all messages for a room in chronological order (createdAt ASC)."""
        cur = self._conn.execute(
            "SELECT id, room_id, sender, content, created_at FROM messages WHERE room_id = ? ORDER BY created_at ASC",
            (room_id,),
        )
        return [
            {
                "id": row[0],
                "room_id": row[1],
                "sender": row[2],
                "content": row[3],
                "created_at": row[4],
            }
            for row in cur.fetchall()
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_room(row: tuple) -> dict:
        return {
            "id": row[0],
            "status": row[1],
            "created_at": row[2],
            "closed_at": row[3],
            "report": json.loads(row[4]) if row[4] else None,
        }
