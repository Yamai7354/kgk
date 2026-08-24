from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from events.models import EventType
from kernel import KnowledgeGraphKernel
from models import EntityCreate, StatementCreate
from provenance import ProvenanceRecord


class IngestRequest(BaseModel):
    subject: EntityCreate
    relation_label: str
    relation_type: str = "Relation"
    object: EntityCreate
    provenance: ProvenanceRecord
    namespace: str = "global"
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


def create_app(kernel: KnowledgeGraphKernel | None = None) -> FastAPI:
    kgk = kernel or KnowledgeGraphKernel()
    app = FastAPI(title="Knowledge Graph Kernel", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/statements")
    def ingest_statement(body: IngestRequest) -> dict[str, Any]:
        from models import RelationCreate

        result = kgk.ingest(
            StatementCreate(
                subject=body.subject,
                relation=RelationCreate(label=body.relation_label, type=body.relation_type),
                object=body.object,
                provenance=body.provenance,
                namespace=body.namespace,
                properties=body.properties,
            )
        )
        return {
            "statement_id": result.statement.id,
            "subject_id": result.subject.id,
            "relation_id": result.relation.id,
            "object_id": result.object.id,
        }

    @app.get("/statements/{statement_id}")
    def get_statement(statement_id: str) -> dict[str, Any]:
        result = kgk.retrieve.get_statement(statement_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Statement not found")
        return result.statement.model_dump(mode="json")

    @app.get("/entities")
    def get_entities() -> list[dict[str, Any]]:
        entities = kgk.store.all_entities()
        return [e.model_dump(mode="json") for e in entities]

    @app.get("/entities/{entity_id}")
    def get_entity(entity_id: str) -> dict[str, Any]:
        entity = kgk.store.get_entity(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity.model_dump(mode="json")

    @app.get("/entities/{entity_id}/statements")
    def statements_for_entity(entity_id: str, direction: str = "both") -> list[dict[str, Any]]:
        if direction not in ("subject", "object", "both"):
            raise HTTPException(
                status_code=400,
                detail="Invalid direction. Must be 'subject', 'object', or 'both'",
            )
        results = []
        if direction in ("subject", "both"):
            results.extend(kgk.retrieve.by_subject(entity_id))
        if direction in ("object", "both"):
            obj_results = kgk.retrieve.by_object(entity_id)
            seen_ids = {r.statement.id for r in results}
            for r in obj_results:
                if r.statement.id not in seen_ids:
                    results.append(r)
        return [r.statement.model_dump(mode="json") for r in results]

    @app.get("/entities/{entity_id}/neighborhood")
    def entity_neighborhood(entity_id: str, depth: int = 1) -> dict[str, Any]:
        subgraph = kgk.retrieve.neighborhood(entity_id, depth=depth)
        return {
            "root_entity_id": subgraph.root_entity_id,
            "depth": subgraph.depth,
            "statements": [r.statement.model_dump(mode="json") for r in subgraph.statements],
        }

    @app.post("/statements/{statement_id}/retract")
    def retract_statement(statement_id: str, body: RetractRequest) -> dict[str, Any]:
        try:
            result = kgk.retract(statement_id, body.reason, actor=body.actor)
        except KeyError:
            raise HTTPException(status_code=404, detail="Statement not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return result.statement.model_dump(mode="json")

    @app.post("/statements/{statement_id}/supersede")
    def supersede_statement(statement_id: str, body: SupersedeRequest) -> dict[str, Any]:
        from models import RelationCreate

        new_stmt_result = kgk.ingest(
            StatementCreate(
                subject=body.new_subject,
                relation=RelationCreate(label=body.new_relation_label, type=body.new_relation_type),
                object=body.new_object,
                provenance=body.provenance,
            )
        )
        try:
            old_stmt, new_stmt = kgk.supersede(
                statement_id, new_stmt_result.statement, reason=body.reason, actor=body.actor
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Statement not found") from None
        return {
            "old_statement": old_stmt.model_dump(mode="json"),
            "new_statement": new_stmt.model_dump(mode="json"),
        }

    @app.get("/statements/{statement_id}/chain")
    def get_supersession_chain(statement_id: str) -> dict[str, Any]:
        try:
            chain = kgk.resolve_supersession(statement_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Statement not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"statement_id": statement_id, "chain": chain, "active_statement_id": chain[-1]}

    @app.post("/entities/{entity_id}/merge")
    def merge_entities(entity_id: str, body: MergeRequest) -> dict[str, Any]:
        try:
            result = kgk.merge_entities(entity_id, body.duplicate_ids)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "canonical_id": result.canonical_id,
            "merged_ids": result.merged_ids,
            "rewired_statements_count": len(result.rewired_statements),
        }

    @app.post("/entities/{entity_id}/embeddings")
    def upsert_embedding(entity_id: str, body: EmbeddingRequest) -> dict[str, Any]:
        from embeddings.store import EmbeddingRecord

        entity = kgk.store.get_entity(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        record = EmbeddingRecord(entity_id=entity_id, vector=body.vector, model=body.model)
        kgk.embeddings.upsert(record)
        return {"status": "success", "entity_id": entity_id}

    @app.post("/entities/search")
    def search_entities(body: SearchRequest) -> list[dict[str, Any]]:
        results = kgk.embeddings.search(body.vector, top_k=body.top_k)
        hydrated = []
        for r in results:
            entity = kgk.store.get_entity(r.entity_id)
            hydrated.append(
                {
                    "entity": entity.model_dump(mode="json") if entity else None,
                    "entity_id": r.entity_id,
                    "score": r.score,
                }
            )
        return hydrated

    @app.post("/search/hybrid")
    def search_hybrid(body: HybridSearchRequest) -> list[dict[str, Any]]:
        results = kgk.search_hybrid(
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
        target_id: str | None = None,
        event_type: EventType | None = None,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        if target_id:
            events = kgk.events.events_for_target(target_id)
        elif event_type:
            events = kgk.events.events_by_type(event_type)
        elif namespace:
            events = kgk.events.events_for_namespace(namespace)
        else:
            events = kgk.events.all_events()
        return [e.model_dump(mode="json") for e in events]

    @app.get("/conflicts")
    def get_conflicts() -> list[dict[str, Any]]:
        return [c.model_dump(mode="json") for c in kgk.conflicts.all_conflicts()]

    return app


app = create_app()
