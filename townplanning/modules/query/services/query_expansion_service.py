from __future__ import annotations

from townplanning.modules.query.services.acronym_service import (
    AcronymService,
)
from townplanning.modules.query.services.synonym_service import (
    SynonymService,
)


class QueryExpansionService:
    """
    Expands a query using deterministic rules.

    Expansion order:

        Acronyms
            ↓
        Synonyms
    """

    def __init__(
        self,
        acronym_service: AcronymService,
        synonym_service: SynonymService,
    ) -> None:

        self._acronym_service = acronym_service
        self._synonym_service = synonym_service

    def expand(
        self,
        question: str,
    ) -> str:
        """
        Expand a user query.
        """

        expanded = self._acronym_service.expand(
            question,
        )

        expanded = self._synonym_service.expand(
            expanded,
        )

        return expanded