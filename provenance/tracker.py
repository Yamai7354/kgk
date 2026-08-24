from provenance.models import ProvenanceEvent, ProvenanceRecord, Source


class ProvenanceTracker:
    """Provenance tracking with source registry and immutable lineage logging."""

    def __init__(self) -> None:
        self._events: list[ProvenanceEvent] = []
        self._sources: dict[str, Source] = {}

    def register_source(self, source: Source) -> Source:
        self._sources[source.id] = source
        return source

    def get_source(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def record_ingestion(self, statement_id: str, record: ProvenanceRecord) -> ProvenanceEvent:
        event = ProvenanceEvent(
            statement_id=statement_id,
            event_type="ingested",
            record=record,
        )
        self._events.append(event)
        return event

    def record_retraction(
        self, statement_id: str, record: ProvenanceRecord, reason: str
    ) -> ProvenanceEvent:
        event = ProvenanceEvent(
            statement_id=statement_id,
            event_type="retracted",
            record=record.model_copy(update={"metadata": {**record.metadata, "reason": reason}}),
        )
        self._events.append(event)
        return event

    def record_superseded(
        self, statement_id: str, record: ProvenanceRecord, reason: str
    ) -> ProvenanceEvent:
        event = ProvenanceEvent(
            statement_id=statement_id,
            event_type="superseded",
            record=record.model_copy(update={"metadata": {**record.metadata, "reason": reason}}),
        )
        self._events.append(event)
        return event

    def lineage_for(self, statement_id: str) -> list[ProvenanceEvent]:
        return [e for e in self._events if e.statement_id == statement_id]

    @property
    def events(self) -> list[ProvenanceEvent]:
        return list(self._events)
