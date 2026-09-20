import json
import re
from typing import Protocol

from drivers.models import Document, Span
from models.entity import EntityCreate
from models.relation import RelationCreate
from models.statement import StatementCreate
from provenance.models import ProvenanceRecord


class Extractor(Protocol):
    """Abstract interface for extracting knowledge statements from documents."""

    def extract(self, document: Document) -> list[StatementCreate]: ...


class KeyValueExtractor:
    """Extracts statements from lines of 'Key: Value' or 'Key = Value' syntax."""

    def __init__(self, subject_label: str | None = None) -> None:
        self._default_subject = subject_label

    def extract(self, document: Document) -> list[StatementCreate]:
        subject_name = (
            self._default_subject or document.metadata.get("subject") or "DocumentSubject"
        )
        statements: list[StatementCreate] = []

        for line_idx, line in enumerate(document.text.splitlines(), start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            delimiter = ":" if ":" in line_str else "=" if "=" in line_str else None
            if not delimiter:
                continue

            parts = line_str.split(delimiter, 1)
            key = parts[0].strip().replace(" ", "_").lower()
            val = parts[1].strip()

            if not key or not val:
                continue

            span = Span(line_number=line_idx, text_snippet=line_str)
            prov = ProvenanceRecord(
                source=document.source_type,
                source_id=document.id,
                source_uri=document.source_uri,
                metadata={"span": span.model_dump()},
            )

            statements.append(
                StatementCreate(
                    subject=EntityCreate(label=subject_name, namespace=document.namespace),
                    relation=RelationCreate(label=key, namespace=document.namespace),
                    object=EntityCreate(label=val, namespace=document.namespace),
                    provenance=prov,
                    namespace=document.namespace,
                )
            )

        return statements


class PatternExtractor:
    """Extracts statements using regular expression capture groups."""

    def __init__(self, patterns: list[tuple[str, str, int, int]] | None = None) -> None:
        """Patterns are tuples of (regex, relation_label, subject_group, object_group)."""
        self.patterns = patterns or [
            (r"([A-Z][a-zA-Z\s]+)\s+lives in\s+([A-Z][a-zA-Z\s]+)", "lives_in", 1, 2),
            (r"([A-Z][a-zA-Z\s]+)\s+is a\s+([a-zA-Z\s]+)", "is_a", 1, 2),
            (r"([A-Z][a-zA-Z\s]+)\s+works at\s+([A-Z][a-zA-Z\s]+)", "works_at", 1, 2),
        ]

    def extract(self, document: Document) -> list[StatementCreate]:
        statements: list[StatementCreate] = []

        for pattern, rel_label, subj_grp, obj_grp in self.patterns:
            for match in re.finditer(pattern, document.text):
                subj_text = match.group(subj_grp).strip()
                obj_text = match.group(obj_grp).strip()

                span = Span(
                    start_char=match.start(),
                    end_char=match.end(),
                    text_snippet=match.group(0),
                )
                prov = ProvenanceRecord(
                    source=document.source_type,
                    source_id=document.id,
                    source_uri=document.source_uri,
                    metadata={"span": span.model_dump()},
                )

                statements.append(
                    StatementCreate(
                        subject=EntityCreate(label=subj_text, namespace=document.namespace),
                        relation=RelationCreate(label=rel_label, namespace=document.namespace),
                        object=EntityCreate(label=obj_text, namespace=document.namespace),
                        provenance=prov,
                        namespace=document.namespace,
                    )
                )

        return statements


class StructuredJsonExtractor:
    """Extracts statements from JSON objects (e.g. character profiles or entity cards)."""

    def extract(self, document: Document) -> list[StatementCreate]:
        try:
            data = json.loads(document.text)
        except Exception:
            return []

        if not isinstance(data, dict):
            return []

        subject_name = (
            data.get("name") or data.get("label") or document.metadata.get("subject") or "Entity"
        )
        subject_type = data.get("type", "Person")
        statements: list[StatementCreate] = []

        for key, val in data.items():
            if key in ("name", "label", "type"):
                continue

            # If scalar value
            if isinstance(val, str | int | float | bool):
                prov = ProvenanceRecord(
                    source=document.source_type,
                    source_id=document.id,
                    source_uri=document.source_uri,
                    metadata={"key": key},
                )
                statements.append(
                    StatementCreate(
                        subject=EntityCreate(
                            label=subject_name, type=subject_type, namespace=document.namespace
                        ),
                        relation=RelationCreate(label=key, namespace=document.namespace),
                        object=EntityCreate(label=str(val), namespace=document.namespace),
                        provenance=prov,
                        namespace=document.namespace,
                    )
                )
            # If list of values
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str | int | float):
                        prov = ProvenanceRecord(
                            source=document.source_type,
                            source_id=document.id,
                            source_uri=document.source_uri,
                            metadata={"key": key},
                        )
                        statements.append(
                            StatementCreate(
                                subject=EntityCreate(
                                    label=subject_name,
                                    type=subject_type,
                                    namespace=document.namespace,
                                ),
                                relation=RelationCreate(label=key, namespace=document.namespace),
                                object=EntityCreate(label=str(item), namespace=document.namespace),
                                provenance=prov,
                                namespace=document.namespace,
                            )
                        )

        return statements
