from __future__ import annotations

from typing import Any

from .regulatory_context import RegulatoryContext
from .regulatory_context_retriever import (
    RegulatoryContextRetriever,
)
from .regulatory_llm_extractor import (
    RegulatoryLLMExtractor,
)
from .regulatory_validator import (
    RegulatoryExtractionValidator,
)
from .deterministic_regulatory_resolver import (
    DeterministicRegulatoryResolver,
)

class RegulatoryExtractionService:
    """
    Generic source-grounded regulatory extraction pipeline.

    Chroma:
        retrieves evidence.

    Ollama:
        interprets evidence.

    Validator:
        verifies provenance.

    No planning calculations are performed here.
    """

    def __init__(
        self,
        context_retriever: RegulatoryContextRetriever,
        llm_extractor: RegulatoryLLMExtractor,
        validator: RegulatoryExtractionValidator | None = None,
    ):
        self.context_retriever = (
            context_retriever
        )

        self.llm_extractor = llm_extractor

        self.validator = (
            validator
            or RegulatoryExtractionValidator()
        )
        self.deterministic_resolver = DeterministicRegulatoryResolver()

    def extract(
        self,
        query: str,
        requested_fields: list[str] | None = None,
        top_k: int = 20,
        related_regulation_limit: int = 20,
    ) -> dict[str, Any]:

        # context = self.context_retriever.retrieve(
        #     query=query,
        #     requested_fields=requested_fields,
        #     top_k=top_k,
        #     related_regulation_limit=(
        #         related_regulation_limit
        #     ),
        # )
        context = self.context_retriever.retrieve(
        query=query,
        requested_fields=requested_fields,
    )

        if not context.sources:
            return {
                "status": "INSUFFICIENT_RULE_DATA",
                "query": query,
                "requested_fields": requested_fields or [],
                "context": context.to_dict(),
                "extraction": {
                    "regulations": [],
                },
                "regulatory_values": {},
                "errors": [
                    "No authoritative PostgreSQL regulatory source was retrieved."
                ],
            }

        raw_extraction = (
            self.llm_extractor.extract(
                context
            )
        )

        validated = self.validator.validate(
            raw_extraction,
            context,
        )

        return {
            "query": query,
            "requested_fields": (
                requested_fields or []
            ),
            "context": context.to_dict(),
            "extraction": validated,
        }
