import json
import sqlite3
from datetime import datetime

from models.entity import Entity
from models.relation import Relation
from models.statement import Statement, StatementStatus
from storage.sqlite.schema import INIT_SCHEMA_SQL


class SqliteGraphStore:
    """Persistent SQLite-backed implementation of the GraphStore protocol."""

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

    def add_entity(self, entity: Entity) -> Entity:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO entities (id, label, type, namespace, properties_json, merged_into, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.label,
                    entity.type,
                    getattr(entity, "namespace", "global"),
                    json.dumps(entity.properties),
                    entity.merged_into,
                    entity.created_at.isoformat(),
                    entity.updated_at.isoformat(),
                ),
            )
        return entity

    def get_entity(self, entity_id: str) -> Entity | None:
        cursor = self._conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_entity(row)

    def update_entity(self, entity: Entity) -> Entity:
        with self._conn:
            cursor = self._conn.execute(
                """
                UPDATE entities
                SET label = ?, type = ?, namespace = ?, properties_json = ?, merged_into = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    entity.label,
                    entity.type,
                    getattr(entity, "namespace", "global"),
                    json.dumps(entity.properties),
                    entity.merged_into,
                    entity.updated_at.isoformat(),
                    entity.id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Entity not found: {entity.id}")
        return entity

    def add_relation(self, relation: Relation) -> Relation:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO relations (id, label, type, inverse_label, namespace, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    relation.id,
                    relation.label,
                    relation.type,
                    relation.inverse_label,
                    getattr(relation, "namespace", "global"),
                    relation.created_at.isoformat(),
                ),
            )
        return relation

    def get_relation(self, relation_id: str) -> Relation | None:
        cursor = self._conn.execute("SELECT * FROM relations WHERE id = ?", (relation_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_relation(row)

    def add_statement(self, statement: Statement) -> Statement:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO statements (
                    id, subject_id, relation_id, object_id, provenance_json, namespace, properties_json,
                    status, created_at, retracted_at, retraction_reason, superseded_by, valid_from, valid_until, epistemic_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    statement.id,
                    statement.subject_id,
                    statement.relation_id,
                    statement.object_id,
                    statement.provenance.model_dump_json(),
                    statement.namespace,
                    json.dumps(statement.properties),
                    statement.status.value,
                    statement.created_at.isoformat(),
                    statement.retracted_at.isoformat() if statement.retracted_at else None,
                    statement.retraction_reason,
                    statement.superseded_by,
                    statement.valid_from.isoformat() if statement.valid_from else None,
                    statement.valid_until.isoformat() if statement.valid_until else None,
                    statement.epistemic_status.value,
                ),
            )
        return statement

    def get_statement(self, statement_id: str) -> Statement | None:
        cursor = self._conn.execute("SELECT * FROM statements WHERE id = ?", (statement_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_statement(row)

    def update_statement(self, statement: Statement) -> Statement:
        with self._conn:
            cursor = self._conn.execute(
                """
                UPDATE statements
                SET subject_id = ?, relation_id = ?, object_id = ?, provenance_json = ?, namespace = ?, properties_json = ?,
                    status = ?, retracted_at = ?, retraction_reason = ?, superseded_by = ?, valid_from = ?, valid_until = ?, epistemic_status = ?
                WHERE id = ?
                """,
                (
                    statement.subject_id,
                    statement.relation_id,
                    statement.object_id,
                    statement.provenance.model_dump_json(),
                    statement.namespace,
                    json.dumps(statement.properties),
                    statement.status.value,
                    statement.retracted_at.isoformat() if statement.retracted_at else None,
                    statement.retraction_reason,
                    statement.superseded_by,
                    statement.valid_from.isoformat() if statement.valid_from else None,
                    statement.valid_until.isoformat() if statement.valid_until else None,
                    statement.epistemic_status.value,
                    statement.id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Statement not found: {statement.id}")
        return statement

    def statements_for_subject(
        self, subject_id: str, *, status: StatementStatus | None = StatementStatus.ACTIVE
    ) -> list[Statement]:
        if status is not None:
            cursor = self._conn.execute(
                "SELECT * FROM statements WHERE subject_id = ? AND status = ?",
                (subject_id, status.value),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM statements WHERE subject_id = ?", (subject_id,)
            )
        return [self._row_to_statement(r) for r in cursor.fetchall()]

    def statements_for_object(
        self, object_id: str, *, status: StatementStatus | None = StatementStatus.ACTIVE
    ) -> list[Statement]:
        if status is not None:
            cursor = self._conn.execute(
                "SELECT * FROM statements WHERE object_id = ? AND status = ?",
                (object_id, status.value),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM statements WHERE object_id = ?", (object_id,)
            )
        return [self._row_to_statement(r) for r in cursor.fetchall()]

    def statements_by_relation(
        self, relation_id: str, *, status: StatementStatus | None = StatementStatus.ACTIVE
    ) -> list[Statement]:
        if status is not None:
            cursor = self._conn.execute(
                "SELECT * FROM statements WHERE relation_id = ? AND status = ?",
                (relation_id, status.value),
            )
        else:
            cursor = self._conn.execute(
                "SELECT * FROM statements WHERE relation_id = ?", (relation_id,)
            )
        return [self._row_to_statement(r) for r in cursor.fetchall()]

    def all_entities(self) -> list[Entity]:
        cursor = self._conn.execute("SELECT * FROM entities")
        return [self._row_to_entity(r) for r in cursor.fetchall()]

    def all_relations(self) -> list[Relation]:
        cursor = self._conn.execute("SELECT * FROM relations")
        return [self._row_to_relation(r) for r in cursor.fetchall()]

    def all_statements(self, *, status: StatementStatus | None = None) -> list[Statement]:
        if status is not None:
            cursor = self._conn.execute(
                "SELECT * FROM statements WHERE status = ?", (status.value,)
            )
        else:
            cursor = self._conn.execute("SELECT * FROM statements")
        return [self._row_to_statement(r) for r in cursor.fetchall()]

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        return Entity(
            id=row["id"],
            label=row["label"],
            type=row["type"],
            namespace=row["namespace"],
            properties=json.loads(row["properties_json"]),
            merged_into=row["merged_into"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_relation(self, row: sqlite3.Row) -> Relation:
        return Relation(
            id=row["id"],
            label=row["label"],
            type=row["type"],
            inverse_label=row["inverse_label"],
            namespace=row["namespace"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_statement(self, row: sqlite3.Row) -> Statement:
        from provenance.models import ProvenanceRecord

        return Statement(
            id=row["id"],
            subject_id=row["subject_id"],
            relation_id=row["relation_id"],
            object_id=row["object_id"],
            provenance=ProvenanceRecord.model_validate_json(row["provenance_json"]),
            namespace=row["namespace"],
            properties=json.loads(row["properties_json"]),
            status=StatementStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            retracted_at=datetime.fromisoformat(row["retracted_at"])
            if row["retracted_at"]
            else None,
            retraction_reason=row["retraction_reason"],
            superseded_by=row["superseded_by"],
            valid_from=datetime.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
            valid_until=datetime.fromisoformat(row["valid_until"]) if row["valid_until"] else None,
            epistemic_status=row["epistemic_status"],
        )
