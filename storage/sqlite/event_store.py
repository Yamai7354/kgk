import json
import sqlite3
from datetime import datetime

from events.models import EventType, KnowledgeEvent
from storage.sqlite.schema import INIT_SCHEMA_SQL


class SqliteEventStore:
    """Persistent SQLite-backed implementation of the append-only EventStore protocol."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.executescript(INIT_SCHEMA_SQL)

    def close(self) -> None:
        self._conn.close()

    def append(self, event: KnowledgeEvent) -> KnowledgeEvent:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, namespace, timestamp, actor, target_id, reason, metadata_json, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type.value,
                    event.namespace,
                    event.timestamp.isoformat(),
                    event.actor,
                    event.target_id,
                    event.reason,
                    json.dumps(event.metadata),
                    json.dumps(event.payload),
                ),
            )
        return event

    def get(self, event_id: str) -> KnowledgeEvent | None:
        cursor = self._conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_event(row)

    def events_for_target(self, target_id: str) -> list[KnowledgeEvent]:
        cursor = self._conn.execute(
            "SELECT * FROM events WHERE target_id = ? ORDER BY timestamp ASC", (target_id,)
        )
        return [self._row_to_event(r) for r in cursor.fetchall()]

    def events_by_type(self, event_type: EventType) -> list[KnowledgeEvent]:
        cursor = self._conn.execute(
            "SELECT * FROM events WHERE event_type = ? ORDER BY timestamp ASC",
            (event_type.value,),
        )
        return [self._row_to_event(r) for r in cursor.fetchall()]

    def events_for_namespace(self, namespace: str) -> list[KnowledgeEvent]:
        cursor = self._conn.execute(
            "SELECT * FROM events WHERE namespace = ? ORDER BY timestamp ASC", (namespace,)
        )
        return [self._row_to_event(r) for r in cursor.fetchall()]

    def all_events(self) -> list[KnowledgeEvent]:
        cursor = self._conn.execute("SELECT * FROM events ORDER BY timestamp ASC")
        return [self._row_to_event(r) for r in cursor.fetchall()]

    def _row_to_event(self, row: sqlite3.Row) -> KnowledgeEvent:
        return KnowledgeEvent(
            event_id=row["event_id"],
            event_type=EventType(row["event_type"]),
            namespace=row["namespace"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            actor=row["actor"],
            target_id=row["target_id"],
            reason=row["reason"],
            metadata=json.loads(row["metadata_json"]),
            payload=json.loads(row["payload_json"]),
        )
