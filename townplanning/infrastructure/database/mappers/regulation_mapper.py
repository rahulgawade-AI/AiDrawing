"""
Converts between Domain and ORM objects.
"""

from townplanning.infrastructure.database.models import RegulationModel


from datetime import datetime, UTC
from townplanning.modules.regulations.ingestion.regulation_document import (
    RegulationDocument,
)
from datetime import datetime, UTC

class RegulationMapper:

    @staticmethod
    def to_model(
         regulation: RegulationDocument,
    ) -> RegulationModel:

        return RegulationModel(

    id=regulation.id,

    number=regulation.number,

    chapter=f"{regulation.chapter_number} - {regulation.chapter_title}",

    title=regulation.title,

    text=regulation.text,

    page_start=regulation.start_page,

    page_end=regulation.end_page,

    source_document="UDCPR",

    version="2020",

    metadata_json={
        "language": regulation.language,
    },

    created_at=datetime.now(UTC),
)
    @staticmethod
    def to_domain(
        model: RegulationModel,
    ) -> RegulationDocument:

        return RegulationDocument(

    id=model.id,

    number=model.number,

    title=model.title,

    chapter_number=model.chapter.split(" - ")[0],

    chapter_title=" - ".join(model.chapter.split(" - ")[1:]),

    language=model.metadata_json.get("language", "en"),

    start_page=model.page_start,

    end_page=model.page_end,

    text=model.text,

    tables=[],
)