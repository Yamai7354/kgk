import os
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from events.models import EventType
from kernel import KnowledgeGraphKernel
from models import EntityCreate, StatementCreate
from namespaces import Namespace, NamespaceAccessError, NamespaceScope
from provenance import ProvenanceRecord


class IngestRequest(BaseModel):
    subject: EntityCreate
    relation_label: str
    relation_type: str = "Relation"
    object: EntityCreate
    provenance: ProvenanceRecord
    namespace: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class RetractRequest(BaseModel):
    reason: str
    actor: str = "system"


class SupersedeRequest(BaseModel):
    new_subject: EntityCreate
    new_relation_label: str
    new_relation_type: str = "Relation"
    new_object: EntityCreate
    provenance: ProvenanceRecord
    reason: str = "superseded"
    actor: str = "system"


class MergeRequest(BaseModel):
    duplicate_ids: list[str]


class EmbeddingRequest(BaseModel):
    vector: list[float]
    model: str = "default"


class SearchRequest(BaseModel):
    vector: list[float]
    top_k: int = 10


class HybridSearchRequest(BaseModel):
    query_text: str | None = None
    query_vector: list[float] | None = None
    top_k: int = 10


class NamespaceRegistrationRequest(BaseModel):
    id: str
    parent_id: str | None = "global"
    description: str | None = None
    priority: int = 50
    is_read_only: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


NamespaceAuthorizer = Callable[[str, str, str], bool]


def create_app(
    kernel: KnowledgeGraphKernel | None = None,
    authorize_namespace: NamespaceAuthorizer | None = None,
) -> FastAPI:
    kgk = kernel or KnowledgeGraphKernel()
    app = FastAPI(title="Knowledge Graph Kernel", version="1.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    def get_scope(
        namespace: Annotated[str, Header(alias="X-KGK-Namespace")],
        actor: Annotated[str, Header(alias="X-KGK-Actor")] = "api-client",
    ) -> NamespaceScope:
        if authorize_namespace is not None and not authorize_namespace(
            actor, namespace, "access"
        ):
            raise HTTPException(status_code=403, detail="Namespace capability denied")
        try:
            return kgk.scope(namespace, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None

    Scoped = Annotated[NamespaceScope, Depends(get_scope)]

    @app.post("/namespaces")
    def register_namespace(
        body: NamespaceRegistrationRequest,
        actor: Annotated[str, Header(alias="X-KGK-Actor")] = "api-admin",
    ) -> dict[str, Any]:
        if authorize_namespace is not None and not authorize_namespace(
            actor, body.id, "register"
        ):
            raise HTTPException(status_code=403, detail="Namespace registration denied")
        try:
            namespace = kgk.register_namespace(
                Namespace(
                    id=body.id,
                    parent_id=body.parent_id,
                    description=body.description,
                    priority=body.priority,
                    is_read_only=body.is_read_only,
                    metadata=body.metadata,
                ),
                actor=actor,
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return namespace.model_dump(mode="json")

    @app.post("/statements")
    def ingest_statement(body: IngestRequest, scope: Scoped) -> dict[str, Any]:
        from models import RelationCreate

        if body.namespace is not None and body.namespace != scope.namespace:
            raise HTTPException(status_code=403, detail="Body namespace does not match capability")
        try:
            result = scope.ingest(
                StatementCreate(
                    subject=body.subject.model_copy(update={"namespace": scope.namespace}),
                    relation=RelationCreate(
                        label=body.relation_label,
                        type=body.relation_type,
                        namespace=scope.namespace,
                    ),
                    object=body.object.model_copy(update={"namespace": scope.namespace}),
                    provenance=body.provenance,
                    namespace=scope.namespace,
                    properties=body.properties,
                )
            )
        except NamespaceAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return {
            "statement_id": result.statement.id,
            "subject_id": result.subject.id,
            "relation_id": result.relation.id,
            "object_id": result.object.id,
        }

    @app.get("/statements/{statement_id}")
    def get_statement(statement_id: str, scope: Scoped) -> dict[str, Any]:
        try:
            result = scope.get_statement(statement_id)
        except NamespaceAccessError:
            result = None
        if result is None:
            raise HTTPException(status_code=404, detail="Statement not found")
        return result.statement.model_dump(mode="json")

    @app.get("/entities")
    def get_entities(scope: Scoped) -> list[dict[str, Any]]:
        entities = scope.all_entities()
        return [e.model_dump(mode="json") for e in entities]

    @app.get("/entities/{entity_id}")
    def get_entity(entity_id: str, scope: Scoped) -> dict[str, Any]:
        try:
            entity = scope.get_entity(entity_id)
        except NamespaceAccessError:
            entity = None
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity.model_dump(mode="json")

    @app.get("/entities/{entity_id}/statements")
    def statements_for_entity(
        entity_id: str, scope: Scoped, direction: str = "both"
    ) -> list[dict[str, Any]]:
        if direction not in ("subject", "object", "both"):
            raise HTTPException(
                status_code=400,
                detail="Invalid direction. Must be 'subject', 'object', or 'both'",
            )
        results = []
        if direction in ("subject", "both"):
            results.extend(scope.query(subject_id=entity_id))
        if direction in ("object", "both"):
            obj_results = scope.query(object_id=entity_id)
            seen_ids = {r.statement.id for r in results}
            for r in obj_results:
                if r.statement.id not in seen_ids:
                    results.append(r)
        return [r.statement.model_dump(mode="json") for r in results]

    @app.get("/entities/{entity_id}/neighborhood")
    def entity_neighborhood(
        entity_id: str, scope: Scoped, depth: int = 1
    ) -> dict[str, Any]:
        try:
            entity = scope.get_entity(entity_id)
        except NamespaceAccessError:
            entity = None
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        subgraph = kgk.retrieve.neighborhood(
            entity_id, depth=depth, namespaces=scope.read_namespaces
        )
        return {
            "root_entity_id": subgraph.root_entity_id,
            "depth": subgraph.depth,
            "statements": [r.statement.model_dump(mode="json") for r in subgraph.statements],
        }

    @app.post("/statements/{statement_id}/retract")
    def retract_statement(
        statement_id: str, body: RetractRequest, scope: Scoped
    ) -> dict[str, Any]:
        try:
            result = scope.retract(statement_id, body.reason, actor=body.actor)
        except KeyError:
            raise HTTPException(status_code=404, detail="Statement not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except NamespaceAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return result.statement.model_dump(mode="json")

    @app.post("/statements/{statement_id}/supersede")
    def supersede_statement(
        statement_id: str, body: SupersedeRequest, scope: Scoped
    ) -> dict[str, Any]:
        from models import RelationCreate

        try:
            existing = scope.get_statement(statement_id)
            if existing is None:
                raise KeyError(statement_id)
            if existing.statement.namespace != scope.namespace:
                raise NamespaceAccessError(
                    "Inherited knowledge cannot be superseded through a child namespace"
                )
            new_stmt_result = scope.ingest(
                StatementCreate(
                    subject=body.new_subject.model_copy(update={"namespace": scope.namespace}),
                    relation=RelationCreate(
                        label=body.new_relation_label,
                        type=body.new_relation_type,
                        namespace=scope.namespace,
                    ),
                    object=body.new_object.model_copy(update={"namespace": scope.namespace}),
                    provenance=body.provenance,
                    namespace=scope.namespace,
                )
            )
            old_stmt, new_stmt = scope.supersede(
                statement_id,
                new_stmt_result.statement,
                reason=body.reason,
                actor=body.actor,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Statement not found") from None
        except NamespaceAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return {
            "old_statement": old_stmt.model_dump(mode="json"),
            "new_statement": new_stmt.model_dump(mode="json"),
        }

    @app.get("/statements/{statement_id}/chain")
    def get_supersession_chain(statement_id: str, scope: Scoped) -> dict[str, Any]:
        try:
            if scope.get_statement(statement_id) is None:
                raise KeyError(statement_id)
            chain = kgk.resolve_supersession(statement_id)
            for chained_id in chain:
                if scope.get_statement(chained_id) is None:
                    raise KeyError(chained_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Statement not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"statement_id": statement_id, "chain": chain, "active_statement_id": chain[-1]}

    @app.post("/entities/{entity_id}/merge")
    def merge_entities(entity_id: str, body: MergeRequest, scope: Scoped) -> dict[str, Any]:
        try:
            result = scope.merge_entities(entity_id, body.duplicate_ids)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except NamespaceAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return {
            "canonical_id": result.canonical_id,
            "merged_ids": result.merged_ids,
            "rewired_statements_count": len(result.rewired_statements),
        }

    @app.post("/entities/{entity_id}/embeddings")
    def upsert_embedding(
        entity_id: str, body: EmbeddingRequest, scope: Scoped
    ) -> dict[str, Any]:
        from embeddings.store import EmbeddingRecord

        try:
            entity = scope.get_entity(entity_id)
        except NamespaceAccessError:
            entity = None
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        record = EmbeddingRecord(entity_id=entity_id, vector=body.vector, model=body.model)
        kgk.embeddings.upsert(record)
        return {"status": "success", "entity_id": entity_id}

    @app.post("/entities/search")
    def search_entities(body: SearchRequest, scope: Scoped) -> list[dict[str, Any]]:
        results = kgk.embeddings.search(body.vector, top_k=body.top_k)
        hydrated = []
        for r in results:
            entity = kgk.store.get_entity(r.entity_id)
            if entity is None or entity.namespace not in scope.read_namespaces:
                continue
            hydrated.append(
                {
                    "entity": entity.model_dump(mode="json") if entity else None,
                    "entity_id": r.entity_id,
                    "score": r.score,
                }
            )
        return hydrated

    @app.post("/search/hybrid")
    def search_hybrid(body: HybridSearchRequest, scope: Scoped) -> list[dict[str, Any]]:
        results = scope.search_hybrid(
            query_text=body.query_text,
            query_vector=body.query_vector,
            top_k=body.top_k,
        )
        return [
            {
                "entity_id": r.entity.id,
                "label": r.entity.label,
                "type": r.entity.type,
                "rrf_score": r.rrf_score,
                "keyword_rank": r.keyword_rank,
                "vector_rank": r.vector_rank,
            }
            for r in results
        ]

    @app.get("/events")
    def get_events(
        scope: Scoped,
        target_id: str | None = None,
        event_type: EventType | None = None,
    ) -> list[dict[str, Any]]:
        events = scope.events()
        if target_id:
            events = [event for event in events if event.target_id == target_id]
        if event_type:
            events = [event for event in events if event.event_type == event_type]
        return [e.model_dump(mode="json") for e in events]

    @app.get("/conflicts")
    def get_conflicts(scope: Scoped) -> list[dict[str, Any]]:
        allowed = set(scope.read_namespaces)
        visible = []
        for conflict in kgk.conflicts.all_conflicts():
            statements = [kgk.store.get_statement(sid) for sid in conflict.statement_ids]
            if statements and all(stmt is not None and stmt.namespace in allowed for stmt in statements):
                visible.append(conflict.model_dump(mode="json"))
        return visible

    return app


def _default_kernel() -> KnowledgeGraphKernel:
    db_path = os.getenv("KGK_DB_PATH")
    return KnowledgeGraphKernel.persistent(db_path) if db_path else KnowledgeGraphKernel()


app = create_app(_default_kernel())
