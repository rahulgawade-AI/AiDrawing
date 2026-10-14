from __future__ import annotations

import re
from typing import Any

from .regulatory_context import RegulatoryContext


class RegulatoryExtractionValidator:
    """
    Lightweight provenance validator.

    It does not determine whether a regulation applies.

    It verifies that extracted values have identifiable source evidence.
    """

    def validate(
        self,
        extracted: dict[str, Any],
        context: RegulatoryContext,
    ) -> dict[str, Any]:

        source_map = {
            source.source_id: source
            for source in context.sources
        }

        regulations = extracted.get(
            "regulations",
            [],
        )

        if not isinstance(regulations, list):
            raise ValueError(
                "Invalid extraction: regulations must be a list"
            )

        accepted_regulations = []

        for regulation in regulations:

            if not isinstance(regulation, dict):
                continue

            concepts = regulation.get(
                "concepts",
                [],
            )

            if not isinstance(concepts, list):
                concepts = []

            accepted_concepts = []

            for concept in concepts:

                if not isinstance(concept, dict):
                    continue

                source_refs = concept.get(
                    "source_refs",
                    [],
                )

                if not isinstance(source_refs, list):
                    source_refs = []

                valid_refs = [
                    ref
                    for ref in source_refs
                    if str(ref) in source_map
                ]

                # We require source provenance.
                if not valid_refs:
                    continue

                source_text = str(
                    concept.get(
                        "source_text",
                        "",
                    )
                    or ""
                ).strip()

                if not source_text:
                    continue

                # Ensure the claimed source text exists in
                # at least one supplied source.
                source_supported = any(
                    self._text_supported(
                        source_text,
                        source_map[ref].text,
                    )
                    for ref in valid_refs
                )

                if not source_supported:
                    continue

                concept = dict(concept)
                concept["source_refs"] = valid_refs
                concept["validated"] = True

                accepted_concepts.append(
                    concept
                )

            if accepted_concepts:
                regulation = dict(regulation)
                regulation["concepts"] = (
                    accepted_concepts
                )
                accepted_regulations.append(
                    regulation
                )

        return {
            "regulations": accepted_regulations,
            "validation": {
                "input_regulations": len(
                    regulations
                ),
                "accepted_regulations": len(
                    accepted_regulations
                ),
                "accepted_values": sum(
                    len(
                        r.get(
                            "concepts",
                            [],
                        )
                    )
                    for r in accepted_regulations
                ),
            },
        }

    @staticmethod
    def _text_supported(
        source_text: str,
        source: str,
    ) -> bool:

        normalized_claim = (
            re.sub(
                r"\s+",
                " ",
                source_text,
            )
            .strip()
            .lower()
        )

        normalized_source = (
            re.sub(
                r"\s+",
                " ",
                source,
            )
            .strip()
            .lower()
        )

        if not normalized_claim:
            return False

        return normalized_claim in normalized_source
