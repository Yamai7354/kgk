from typing import Any

from retrieval.engine import RetrievalResult


class SubgraphFormatter:
    """Formats knowledge subgraphs into token-budgeted prompt context representations."""

    def format_markdown(
        self,
        statements: list[RetrievalResult],
        *,
        max_chars: int = 4000,
        include_provenance: bool = True,
    ) -> str:
        lines: list[str] = []
        current_len = 0

        for r in statements:
            subj_label = r.subject.label if r.subject else r.statement.subject_id
            rel_label = r.relation.label if r.relation else r.statement.relation_id
            obj_label = r.object.label if r.object else r.statement.object_id

            prov_str = ""
            if include_provenance:
                conf = r.statement.provenance.confidence
                conf_str = f"conf={conf}" if conf is not None else ""
                auth = r.statement.provenance.authority
                auth_str = f"auth={auth}" if auth is not None else ""
                status_str = f"status={r.statement.epistemic_status.value}"
                details = ", ".join(filter(None, [status_str, conf_str, auth_str]))
                prov_str = f" ({details})"

            line = f"- [{subj_label}] --({rel_label})--> [{obj_label}]{prov_str}"
            if current_len + len(line) + 1 > max_chars:
                lines.append("... [truncated due to context budget]")
                break

            lines.append(line)
            current_len += len(line) + 1

        return "\n".join(lines)

    def format_mermaid(
        self,
        statements: list[RetrievalResult],
        *,
        max_chars: int = 4000,
    ) -> str:
        lines: list[str] = ["graph LR"]
        current_len = len("graph LR\n")
        seen_nodes: dict[str, str] = {}
        node_counter = 1

        for r in statements:
            subj_id = r.statement.subject_id
            obj_id = r.statement.object_id

            if subj_id not in seen_nodes:
                node_var = f"N{node_counter}"
                node_counter += 1
                seen_nodes[subj_id] = node_var
                subj_label = r.subject.label if r.subject else subj_id
                lines.append(f'    {node_var}["{subj_label}"]')

            if obj_id not in seen_nodes:
                node_var = f"N{node_counter}"
                node_counter += 1
                seen_nodes[obj_id] = node_var
                obj_label = r.object.label if r.object else obj_id
                lines.append(f'    {node_var}["{obj_label}"]')

            rel_label = r.relation.label if r.relation else r.statement.relation_id
            edge_line = f"    {seen_nodes[subj_id]} -->|{rel_label}| {seen_nodes[obj_id]}"

            if current_len + len(edge_line) + 1 > max_chars:
                lines.append("    %% truncated due to budget")
                break

            lines.append(edge_line)
            current_len += len(edge_line) + 1

        return "\n".join(lines)

    def format_json_ld(
        self,
        statements: list[RetrievalResult],
    ) -> list[dict[str, Any]]:
        graph = []
        for r in statements:
            graph.append(
                {
                    "@id": r.statement.id,
                    "subject": {
                        "id": r.statement.subject_id,
                        "label": r.subject.label if r.subject else None,
                        "type": r.subject.type if r.subject else None,
                    },
                    "predicate": {
                        "id": r.statement.relation_id,
                        "label": r.relation.label if r.relation else None,
                    },
                    "object": {
                        "id": r.statement.object_id,
                        "label": r.object.label if r.object else None,
                        "type": r.object.type if r.object else None,
                    },
                    "epistemic_status": r.statement.epistemic_status.value,
                    "provenance": r.statement.provenance.model_dump(mode="json"),
                }
            )
        return graph
