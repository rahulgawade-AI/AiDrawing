from __future__ import annotations

from townplanning.modules.retrieval.domain.source_document import SourceDocument
from townplanning.modules.retrieval.domain.source_type import SourceType
from townplanning.modules.retrieval.utils.text_formatter import TextFormatter

class DocumentRetrievalService:

    def __init__(
        self,
        ocr_repository,
        regulation_repository,
        rule_repository,
        table_repository,
        knowledge_repository,
    ):

        self._ocr = ocr_repository
        self._regulation = regulation_repository
        self._rule = rule_repository
        self._table = table_repository
        self._knowledge = knowledge_repository


    def _section(self, title: str, value) -> str:

        text = TextFormatter.format(value)

        if not text.strip():
            return ""

        return f"{title}\n{text}"

    ##################################################################
    # OCR
    ##################################################################

    def get_ocr_documents(self) -> list[SourceDocument]:

        records = self._ocr.list()

        return [

            SourceDocument(

                source_type=SourceType.OCR,

                source_id=str(record.id),

                title=f"{record.source} - Page {record.page_number}",

                text=record.translated_text or record.original_text,

                page_number=record.page_number,

                metadata=record.metadata,

            )

            for record in records

        ]

    ##################################################################
    # Regulations
    ##################################################################

    def get_regulations(self) -> list[SourceDocument]:

        regulations = self._regulation.list()

        return [

            SourceDocument(

                source_type=SourceType.REGULATION,

                source_id=regulation.id,

                title=f"{regulation.number} - {regulation.title}",

                text=regulation.text,

                page_number=regulation.start_page,

                metadata={

                    "regulation_number": regulation.number,

                    "chapter_number": regulation.chapter_number,

                    "chapter_title": regulation.chapter_title,

                    "language": regulation.language,

                    "start_page": regulation.start_page,

                    "end_page": regulation.end_page,

                },

            )

            for regulation in regulations

        ]

    ##################################################################
    # Rules
    ##################################################################

    def get_rules(self) -> list[SourceDocument]:

        rules = self._rule.list()

        documents = []

        for rule in rules:

            text = "\n".join(

                [

                    f"Rule: {rule.name}",

                    f"Category: {rule.category}",

                    "",

                    rule.description,

                    "",

                    f"Condition: {rule.condition}",

                    "",

                    f"Result: {rule.result}",

                ]

            )

            documents.append(

                SourceDocument(

                    source_type=SourceType.RULE,

                    source_id=rule.id,

                    title=rule.name,

                    text=text,

                    metadata={

                        "regulation_id": rule.regulation_id,

                        "priority": rule.priority,

                        "enabled": rule.enabled,

                        **rule.metadata,

                    },

                )

            )

        return documents

    ##################################################################
    # Tables
    ##################################################################

    def get_tables(self) -> list[SourceDocument]:

        tables = self._table.list()

        return [

            SourceDocument(

                source_type=SourceType.TABLE,

                source_id=table.id,

                title=table.title,

                text=table.markdown,

                page_number=table.page,

                metadata={

                    "table_index": table.index,

                    "headers": table.headers,

                    "rows": len(table.rows),

                    **table.metadata,

                },

            )

            for table in tables

        ]

    ##################################################################
    # Knowledge Cards
    ##################################################################

    def get_knowledge_cards(self) -> list[SourceDocument]:

        cards = self._knowledge.list()

        documents = []

        for card in cards:
            parts = [

             self._section("Summary", card.summary),

             self._section("Purpose", card.purpose),

             self._section("Scope", card.scope),

             self._section("Definitions", card.definitions),

             self._section("Permissions", card.permissions),

             self._section("Conditions", card.conditions),

             self._section("Prohibitions", card.prohibitions),

             self._section("Measurements", card.measurements),

             self._section("Exceptions", card.exceptions),

             self._section("Applicability", card.applicability),

             self._section("Authority", card.authority),

             self._section("Inputs", card.inputs),

             self._section("Outputs", card.outputs),

             self._section("References", card.references),

             self._section("Related Regulations", card.related_regulations),

             self._section("Keywords", card.keywords),

             self._section("Examples", card.examples),

             self._section("Notes", card.notes),

        ]
            text = "\n\n".join(
            part for part in parts if part
            )

           
            

            documents.append(

                SourceDocument(

                    source_type=SourceType.KNOWLEDGE_CARD,

                    source_id=card.id,

                    title=card.title,

                    text=text,

                    metadata={

                        "regulation_id": card.regulation_id,

                        "authority": card.authority,

                        "inputs": card.inputs,

                        "outputs": card.outputs,

                        "keywords": card.keywords,

                        **card.metadata,

                    },

                )

            )

        return documents

    

    ##################################################################
    # All Documents
    ##################################################################

    def get_all_documents(self) -> list[SourceDocument]:

        documents: list[SourceDocument] = []

        documents.extend(self.get_ocr_documents())

        documents.extend(self.get_regulations())

        documents.extend(self.get_rules())

        documents.extend(self.get_tables())

        documents.extend(self.get_knowledge_cards())

        return documents