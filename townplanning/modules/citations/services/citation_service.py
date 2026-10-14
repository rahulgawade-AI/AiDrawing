from __future__ import annotations

from townplanning.modules.citations.domain.citation import Citation
from townplanning.modules.search.dom.search_result import SearchResult


class CitationService:
    """
    Builds citations from semantic search results.

    This implementation is backward compatible with older vector
    metadata and newer metadata added during ingestion.
    """

    def build(
        self,
        results: list[SearchResult],
    ) -> list[Citation]:

        citations: list[Citation] = []

        for number, result in enumerate(results, start=1):

            metadata = result.metadata or {}

            # ----------------------------
            # Source / Document Name
            # ----------------------------
            source = (
                metadata.get("document")
                or metadata.get("source")
                or metadata.get("source_file")
                or metadata.get("file_name")
                or metadata.get("filename")
                or metadata.get("pdf_name")
                or metadata.get("pdf")
                or metadata.get("document_name")
                or metadata.get("title")
                or metadata.get("regulation_number")
                or metadata.get("chapter_title")
                or metadata.get("authority")
                or f"Search Result {number}"
            )

            # ----------------------------
            # Title
            # ----------------------------
            title = (
                metadata.get("title")
                or metadata.get("rule_name")
                or metadata.get("chapter_title")
                or metadata.get("regulation_number")
            )

            # ----------------------------
            # Page
            # ----------------------------
            page = (
                metadata.get("page_number")
                or metadata.get("page")
                or metadata.get("start_page")
            )

            citations.append(
                Citation(
                    number=number,
                    source=str(source),
                    title=title,
                    page=page,
                    metadata=metadata,
                )
            )

        return citations