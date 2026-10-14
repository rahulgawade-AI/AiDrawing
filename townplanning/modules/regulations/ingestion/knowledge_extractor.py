"""
AI Knowledge Extractor.

Input:
    PageAnalysis
    PageWindow

Output:
    KnowledgeCard
"""

import json
from pathlib import Path
from uuid import uuid4
from townplanning.ai import AIRequest
#from townplanning.ai import OllamaClient
from townplanning.ai.factory import AIClientFactory

from townplanning.modules.regulations.domain import KnowledgeCard

from uuid import uuid4

from townplanning.modules.regulations.ingestion.regulation_document import (
    RegulationDocument,
)


class KnowledgeExtractor:

    def __init__(self):

        #self.client = OllamaClient()
        self.client = AIClientFactory.create()

        prompt = Path(
            "townplanning/prompts/knowledge_extraction.md"
        )

        self.system_prompt = prompt.read_text(
            encoding="utf-8"
        )

    # ---------------------------------------------------------
    def extract(
    self,
    regulation: RegulationDocument,
) -> KnowledgeCard:
        """
        Extract a structured KnowledgeCard from a complete regulation.
        """

        prompt = self._build_prompt(regulation)

        # response = self.ai_client.generate_json(
        #     system_prompt=self.SYSTEM_PROMPT,
        #     user_prompt=prompt,
        # )

        # data = response

        request = AIRequest(
                system_prompt=self.system_prompt,
                user_prompt=prompt, 
                )

        response = self.client.generate(request)

        if not response.success:
            raise RuntimeError(response.error)

        data = json.loads(response.content)

        return KnowledgeCard(

    id=str(uuid4()),

    regulation_id=regulation.id,

    title=data.get("title", regulation.title),

    summary=data.get("summary", ""),

    purpose=data.get("purpose", ""),

    scope=data.get("scope", ""),

    definitions=data.get("definitions", []),

    permissions=data.get("permissions", []),

    conditions=data.get("conditions", []),

    prohibitions=data.get("prohibitions", []),

    measurements=data.get("measurements", []),

    exceptions=data.get("exceptions", []),

    applicability=data.get("applicability", []),

    authority=data.get("authority", ""),

    inputs=data.get("inputs", []),

    outputs=data.get("outputs", []),

    references=data.get("references", []),

    related_regulations=data.get(
        "related_regulations", []
    ),

    keywords=data.get("keywords", []),

    examples=data.get("examples", []),

    notes=data.get("notes", []),

    metadata=data.get("metadata", {}),
)

    # ---------------------------------------------------------

    def _build_prompt(
    self,
    regulation: RegulationDocument,
) -> str:
        """
        Build the LLM prompt from a complete RegulationDocument.
        """

        tables = ""

        if regulation.tables:

            tables = "\n\n".join(
                table.markdown
                for table in regulation.tables
            )

        return f"""
You are an expert in Maharashtra UDCPR regulations.

Extract ONE Knowledge Card.

Regulation Number:
{regulation.number}

Regulation Title:
{regulation.title}

Chapter:
{regulation.chapter_number} - {regulation.chapter_title}

Pages:
{regulation.start_page} - {regulation.end_page}

==========================
REGULATION TEXT
==========================

{regulation.text}

==========================
TABLES
==========================

{tables}

Return ONLY valid JSON.

Do not include markdown.

Do not invent information.

Only use information explicitly present in the regulation.
"""