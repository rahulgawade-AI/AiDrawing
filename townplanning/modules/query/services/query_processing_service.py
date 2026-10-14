from __future__ import annotations

from townplanning.modules.query.dom.query import (
    Query,
)
from townplanning.modules.query.services.entity_extraction_service import (
    EntityExtractionService,
)
from townplanning.modules.query.services.intent_detection_service import (
    IntentDetectionService,
)
from townplanning.modules.query.services.query_expansion_service import (
    QueryExpansionService,
)


class QueryProcessingService:
    """
    Main Query Processing Pipeline.

    Responsibilities
    ----------------

    1. Detect intent
    2. Extract entities
    3. Expand query
    4. Produce normalized Query object
    """

    def __init__(
        self,
        intent_detection_service: IntentDetectionService,
        entity_extraction_service: EntityExtractionService,
        query_expansion_service: QueryExpansionService,
    ) -> None:

        self._intent_detection = intent_detection_service

        self._entity_extraction = entity_extraction_service

        self._query_expansion = query_expansion_service

    def process(
        self,
        question: str,
    ) -> Query:
        """
        Process a user question.
        """

        normalized = question.strip()

        expanded = self._query_expansion.expand(
            normalized,
        )

        intent = self._intent_detection.detect(
            normalized,
        )

        entities = self._entity_extraction.extract(
            normalized,
        )

        keywords = [
            entity.value
            for entity in entities
        ]

        return Query(
            original=question,
            normalized=normalized,
            expanded=expanded,
            intent=intent,
            entities=entities,
            keywords=keywords,
        )