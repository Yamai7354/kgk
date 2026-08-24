from typing import TYPE_CHECKING

from epistemic.models import Perspective

if TYPE_CHECKING:
    from models.statement import Statement


class AuthorityResolver:
    """Evaluates multi-source assertions and resolves authoritative truth according to policy and perspectives."""

    def compute_statement_score(
        self, statement: "Statement", perspective: Perspective | None = None
    ) -> float:
        prov = statement.provenance
        authority = prov.authority or 0.0

        if perspective is not None:
            # Check for source ID override
            if prov.source_id and prov.source_id in perspective.authority_overrides:
                authority = perspective.authority_overrides[prov.source_id]
            elif prov.source in perspective.authority_overrides:
                authority = perspective.authority_overrides[prov.source]
            elif prov.source in perspective.preferred_sources or (
                prov.source_id and prov.source_id in perspective.preferred_sources
            ):
                authority += 50.0

        confidence = prov.confidence if prov.confidence is not None else 0.5
        recency = statement.created_at.timestamp() / 1e10

        # Lexicographical weight: Authority (primary) > Confidence (secondary) > Recency (tertiary)
        return (authority * 10000.0) + (confidence * 100.0) + recency

    def resolve_winner(
        self, statements: list["Statement"], perspective: Perspective | None = None
    ) -> "Statement | None":
        if not statements:
            return None

        candidates = statements
        if perspective is not None:
            candidates = [
                s for s in statements if s.epistemic_status in perspective.accepted_statuses
            ]
            if not candidates:
                return None

        return max(
            candidates,
            key=lambda s: self.compute_statement_score(s, perspective),
        )

    def filter_perspective(
        self, statements: list["Statement"], perspective: Perspective
    ) -> list["Statement"]:
        return [
            s
            for s in statements
            if s.is_active and s.epistemic_status in perspective.accepted_statuses
        ]
