from typing import Any

from conflicts.models import ConflictStatus
from epistemic.models import EpistemicStatus, Perspective
from ingestion.pipeline import IngestionResult
from kernel import KnowledgeGraphKernel
from models.entity import EntityCreate
from models.relation import RelationCreate
from models.statement import StatementCreate
from namespaces.models import Namespace
from ontology.models import RelationDefinition
from provenance.models import ProvenanceRecord

CANON_AUTHORITY = 100
NARRATIVE_AUTHORITY = 80
OBSERVER_AUTHORITY = 50
RUMOR_AUTHORITY = 20


class MinaCanonClient:
    """Application-layer client for managing Mina character canon, lore, and LLM context formatting."""

    def __init__(
        self,
        kernel: KnowledgeGraphKernel | None = None,
        namespace: str = "mina",
    ) -> None:
        self.kernel = kernel or KnowledgeGraphKernel()
        self.namespace = namespace
        self._setup_canon_rules()

    def _setup_canon_rules(self) -> None:
        # Register namespace hierarchy: mina inherits from global
        self.kernel.namespaces.register(Namespace(id=self.namespace, parent_id="global"))

        # Register core canon ontology schemas
        self.kernel.ontology.register(
            RelationDefinition(
                label="birthplace",
                is_functional=True,
                description="Unique birth location of a character",
            )
        )
        self.kernel.ontology.register(
            RelationDefinition(
                label="real_name",
                is_functional=True,
                description="Canonical legal name of a character",
            )
        )
        self.kernel.ontology.register(
            RelationDefinition(
                label="role",
                is_functional=False,
                description="Occupational role or team position",
            )
        )
        self.kernel.ontology.register(
            RelationDefinition(
                label="trait",
                is_functional=False,
                description="Core personality trait",
            )
        )

    def assert_canon(
        self,
        subject_name: str,
        relation_label: str,
        object_name: str,
        *,
        source: str = "creator_canon",
        subject_type: str = "Character",
        object_type: str = "Concept",
    ) -> IngestionResult:
        """Asserts immutable creator canon truth (authority=100, FACT)."""
        prov = ProvenanceRecord(
            source=source,
            authority=CANON_AUTHORITY,
            confidence=1.0,
        )
        payload = StatementCreate(
            subject=EntityCreate(label=subject_name, type=subject_type, namespace=self.namespace),
            relation=RelationCreate(label=relation_label, namespace=self.namespace),
            object=EntityCreate(label=object_name, type=object_type, namespace=self.namespace),
            provenance=prov,
            namespace=self.namespace,
            epistemic_status=EpistemicStatus.FACT,
        )
        result = self.kernel.ingest(payload)
        self._resolve_pending_conflicts()
        return result

    def record_event(
        self,
        subject_name: str,
        relation_label: str,
        object_name: str,
        *,
        source: str = "narrative_canon",
    ) -> IngestionResult:
        """Records an official narrative storyline event (authority=80, FACT)."""
        prov = ProvenanceRecord(
            source=source,
            authority=NARRATIVE_AUTHORITY,
            confidence=0.95,
        )
        payload = StatementCreate(
            subject=EntityCreate(label=subject_name, namespace=self.namespace),
            relation=RelationCreate(label=relation_label, namespace=self.namespace),
            object=EntityCreate(label=object_name, namespace=self.namespace),
            provenance=prov,
            namespace=self.namespace,
            epistemic_status=EpistemicStatus.FACT,
        )
        result = self.kernel.ingest(payload)
        self._resolve_pending_conflicts()
        return result

    def record_observation(
        self,
        subject_name: str,
        relation_label: str,
        object_name: str,
        *,
        source: str = "user_interaction",
    ) -> IngestionResult:
        """Records an observed behavioral trait or interaction (authority=50, BELIEF)."""
        prov = ProvenanceRecord(
            source=source,
            authority=OBSERVER_AUTHORITY,
            confidence=0.8,
        )
        payload = StatementCreate(
            subject=EntityCreate(label=subject_name, namespace=self.namespace),
            relation=RelationCreate(label=relation_label, namespace=self.namespace),
            object=EntityCreate(label=object_name, namespace=self.namespace),
            provenance=prov,
            namespace=self.namespace,
            epistemic_status=EpistemicStatus.BELIEF,
        )
        result = self.kernel.ingest(payload)
        self._resolve_pending_conflicts()
        return result

    def record_rumor(
        self,
        subject_name: str,
        relation_label: str,
        object_name: str,
        *,
        source: str = "fandom_rumor",
    ) -> IngestionResult:
        """Records an unverified rumor or hypothesis (authority=20, HYPOTHESIS)."""
        prov = ProvenanceRecord(
            source=source,
            authority=RUMOR_AUTHORITY,
            confidence=0.4,
        )
        payload = StatementCreate(
            subject=EntityCreate(label=subject_name, namespace=self.namespace),
            relation=RelationCreate(label=relation_label, namespace=self.namespace),
            object=EntityCreate(label=object_name, namespace=self.namespace),
            provenance=prov,
            namespace=self.namespace,
            epistemic_status=EpistemicStatus.HYPOTHESIS,
        )
        result = self.kernel.ingest(payload)
        self._resolve_pending_conflicts()
        return result

    def _resolve_pending_conflicts(self) -> None:
        for conflict in self.kernel.conflicts.all_conflicts(status=ConflictStatus.OPEN):
            try:
                self.kernel.conflicts.resolve_by_authority(conflict.id)
            except Exception:
                pass

    def get_character_profile(self, character_name: str) -> dict[str, Any]:
        """Returns structured character profile combining active canon facts and observations."""
        match = self.kernel.entities.resolve(character_name, namespace=self.namespace)
        if not match:
            return {"name": character_name, "found": False}

        entity = match.entity
        results = self.kernel.query_scoped(subject_id=entity.id, namespaces=self.namespace)

        profile: dict[str, Any] = {
            "name": entity.label,
            "type": entity.type,
            "namespace": getattr(entity, "namespace", "global"),
            "canon_facts": {},
            "observations": {},
            "rumors": {},
        }

        for r in results:
            rel = r.relation.label if r.relation else r.statement.relation_id
            obj = r.object.label if r.object else r.statement.object_id
            status = r.statement.epistemic_status

            bucket = (
                "canon_facts"
                if status == EpistemicStatus.FACT
                else "observations"
                if status == EpistemicStatus.BELIEF
                else "rumors"
            )
            if rel not in profile[bucket]:
                profile[bucket][rel] = []
            profile[bucket][rel].append(obj)

        return profile

    def build_llm_prompt_context(
        self,
        character_name: str,
        *,
        max_chars: int = 2000,
        include_rumors: bool = False,
    ) -> str:
        """Generates token-budgeted markdown context formatted for LLM system prompt injection."""
        match = self.kernel.entities.resolve(character_name, namespace=self.namespace)
        if not match:
            return f"No verified lore found for {character_name}."

        entity = match.entity
        accepted_statuses = (
            {EpistemicStatus.FACT, EpistemicStatus.BELIEF, EpistemicStatus.HYPOTHESIS}
            if include_rumors
            else {EpistemicStatus.FACT, EpistemicStatus.BELIEF}
        )

        perspective = Perspective(
            name="mina_active_canon",
            accepted_statuses=accepted_statuses,
        )

        statements = self.kernel.view_perspective(
            perspective, subject_id=entity.id, namespaces=self.namespace
        )

        header = f"### [Character Canon: {entity.label}]\n"
        formatted_body = self.kernel.formatter.format_markdown(
            statements, max_chars=max_chars - len(header)
        )
        return f"{header}{formatted_body}"
