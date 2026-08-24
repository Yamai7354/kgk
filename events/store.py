from datetime import datetime
from typing import Protocol

from events.models import EventType, KnowledgeEvent


class EventStore(Protocol):
    """Authoritative append-only log of knowledge events."""

    def append(self, event: KnowledgeEvent) -> KnowledgeEvent: ...

    def get(self, event_id: str) -> KnowledgeEvent | None: ...

    def events_for_target(self, target_id: str) -> list[KnowledgeEvent]: ...

    def events_by_type(self, event_type: EventType) -> list[KnowledgeEvent]: ...

    def events_for_namespace(self, namespace: str) -> list[KnowledgeEvent]: ...

    def events_since(self, timestamp: datetime) -> list[KnowledgeEvent]: ...

    def all_events(self) -> list[KnowledgeEvent]: ...


class InMemoryEventStore:
    """In-memory implementation of the authoritative Knowledge Event Store."""

    def __init__(self) -> None:
        self._events: list[KnowledgeEvent] = []
        self._by_id: dict[str, KnowledgeEvent] = {}

    def append(self, event: KnowledgeEvent) -> KnowledgeEvent:
        self._events.append(event)
        self._by_id[event.event_id] = event
        return event

    def get(self, event_id: str) -> KnowledgeEvent | None:
        return self._by_id.get(event_id)

    def events_for_target(self, target_id: str) -> list[KnowledgeEvent]:
        return [e for e in self._events if e.target_id == target_id]

    def events_by_type(self, event_type: EventType) -> list[KnowledgeEvent]:
        return [e for e in self._events if e.event_type == event_type]

    def events_for_namespace(self, namespace: str) -> list[KnowledgeEvent]:
        return [e for e in self._events if e.namespace == namespace]

    def events_since(self, timestamp: datetime) -> list[KnowledgeEvent]:
        return [e for e in self._events if e.timestamp >= timestamp]

    def all_events(self) -> list[KnowledgeEvent]:
        return list(self._events)
