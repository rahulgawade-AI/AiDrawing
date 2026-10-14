from __future__ import annotations

from townplanning.modules.query.dom.query import (
    Query,
)
from townplanning.modules.query.providers.base_provider import (
    BaseQueryProvider,
)


class NoopQueryProvider(BaseQueryProvider):
    """
    Pass-through provider.
    """

    def process(
        self,
        question: str,
    ) -> Query:

        return Query(
            original=question,
            normalized=question,
            expanded=question,
        )