from __future__ import annotations

import logging

from sqlalchemy import text

from townplanning.infrastructure.database.session import (
    SessionLocal,
)
from townplanning.modules.search.dom.search_result import (
    SearchResult,
)

logger = logging.getLogger(__name__)


class PostgresSearchRepository:
    """
    PostgreSQL Full-Text Search repository.

    Executes BM25-style full-text searches using PostgreSQL's
    tsvector/tsquery engine.
    """

    def search(
        self,
        query: str,
        top_k: int = 50,
    ) -> list[SearchResult]:
        """
        Execute a full-text search.

        Parameters
        ----------
        query:
            User question.

        top_k:
            Maximum results.

        Returns
        -------
        list[SearchResult]
        """

        sql = text(
            """
            SELECT
                id,
                text,
                metadata,
                ts_rank_cd(
                    search_vector,
                    websearch_to_tsquery('english', :query)
                ) AS score
            FROM chunks
            WHERE search_vector @@ websearch_to_tsquery('english', :query)
            ORDER BY score DESC
            LIMIT :top_k
            """
        )

        session = SessionLocal()

        try:

            rows = session.execute(
                sql,
                {
                    "query": query,
                    "top_k": top_k,
                },
            ).mappings()

            results: list[SearchResult] = []

            for row in rows:

                results.append(
                    SearchResult(
                        id=str(row["id"]),
                        score=float(row["score"]),
                        text=row["text"],
                        metadata=row["metadata"] or {},
                    )
                )

            logger.info(
                "BM25 search returned %d results.",
                len(results),
            )

            return results

        finally:

            session.close()