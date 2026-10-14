"""
Table Mapper.
"""

from townplanning.infrastructure.database.models import Table as TableModel
from townplanning.modules.regulations.ingestion.table import ExtractedTable


class TableMapper:

    @staticmethod
    def to_model(
        table: ExtractedTable,
        regulation_id: str,
    ) -> TableModel:

        return TableModel(
            id=table.id,
            regulation_id=regulation_id,
            page_number=table.page,
            table_index=table.index,
            title=table.title,
            headers=table.headers,
            rows=table.rows,
            markdown=table.markdown,
            extra_metadata=table.metadata,
        )

    @staticmethod
    def to_domain(
        model: TableModel,
    ) -> ExtractedTable:

        return ExtractedTable(
            id=model.id,
            page=model.page_number,
            index=model.table_index,
            title=model.title,
            headers=model.headers,
            rows=model.rows,
            markdown=model.markdown,
            metadata=model.extra_metadata,
        )