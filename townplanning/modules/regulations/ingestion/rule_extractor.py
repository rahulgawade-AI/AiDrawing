"""
AI Rule Extractor.

Converts a KnowledgeCard into machine-readable rules.
"""

import json
from pathlib import Path
from uuid import uuid4

from townplanning.ai import AIRequest
#from townplanning.ai import OllamaClient
from townplanning.ai.factory import AIClientFactory
from townplanning.modules.regulations.domain import KnowledgeCard
from townplanning.modules.regulations.domain import Rule
from uuid import uuid4

from townplanning.modules.regulations.ingestion.regulation_document import (
    RegulationDocument,
)
from townplanning.modules.regulations.domain.rule import Rule

class RuleExtractor:

    def __init__(self):

        #self.client = OllamaClient()
        self.client = AIClientFactory.create()

        prompt = Path(
            "townplanning/prompts/rule_extraction.md"
        )

        self.system_prompt = prompt.read_text(
            encoding="utf-8"
        )

    # --------------------------------------------------
   
    def extract(
    self,
    regulation: RegulationDocument,
    knowledge: KnowledgeCard,
) -> list[Rule]:
        """
        Extract executable rules from a complete regulation.
        """

        prompt = self._build_prompt(
            regulation,
            knowledge,
        )

        # response = self.ai_client.generate_json(
        #     system_prompt=self.SYSTEM_PROMPT,
        #     user_prompt=prompt,
        # )


        request = AIRequest(
        system_prompt=self.system_prompt,
            user_prompt=prompt,
        )

        response = self.client.generate(request)

        if not response.success:
            raise RuntimeError(response.error)

        response = json.loads(response.content)

        #
        # Models sometimes return
        #
        # {
        #    "rules":[...]
        # }
        #
        # instead of
        #
        # [...]
        #

        if isinstance(response, dict):

            rules_data = response.get("rules", [])

        else:

            rules_data = response

        if not isinstance(rules_data, list):

            raise ValueError(
                "RuleExtractor expected a list of rules."
            )

        rules = []

        for item in rules_data:

            rules.append(

                Rule(

                    id=str(uuid4()),

                    regulation_id=regulation.id,

                    category=item.get(
                        "category",
                        "General",
                    ),

                    name=item.get(
                        "name",
                        "",
                    ),

                    description=item.get(
                        "description",
                        "",
                    ),

                    condition=item.get(
                        "condition",
                        {},
                    ),

                    result=item.get(
                        "result",
                        {},
                    ),

                    priority=item.get(
                        "priority",
                        100,
                    ),

                    enabled=item.get(
                        "enabled",
                        True,
                    ),

                    metadata=item.get(
                        "metadata",
                        {},
                    ),
                )

            )

        return rules

    # --------------------------------------------------

    
    def _build_prompt(
    self,
    regulation: RegulationDocument,
    knowledge: KnowledgeCard,
) -> str:

        tables = ""

        if regulation.tables:

            tables = "\n\n".join(
                table.markdown
                for table in regulation.tables
            )

        return f"""
You are an expert in Maharashtra UDCPR.

Generate executable rules.

Each rule must contain

- category
- name
- description
- condition
- result
- priority
- enabled
- metadata

Return ONLY JSON.

Regulation Number

{regulation.number}

Regulation Title

{regulation.title}

Chapter

{regulation.chapter_number}
{regulation.chapter_title}

Pages

{regulation.start_page}-{regulation.end_page}

=========================
REGULATION
=========================

{regulation.text}

=========================
TABLES
=========================

{tables}

=========================
KNOWLEDGE CARD
=========================

Title:
{knowledge.title}

Summary:
{knowledge.summary}

Purpose:
{knowledge.purpose}

Scope:
{knowledge.scope}

Authority:
{knowledge.authority}

Applicability:
{knowledge.applicability}

Conditions:
{knowledge.conditions}

Measurements:
{knowledge.measurements}

Exceptions:
{knowledge.exceptions}

Permissions:
{knowledge.permissions}

Prohibitions:
{knowledge.prohibitions}

Definitions:
{knowledge.definitions}

Inputs:
{knowledge.inputs}

Outputs:
{knowledge.outputs}

References:
{knowledge.references}

Related Regulations:
{knowledge.related_regulations}

Keywords:
{knowledge.keywords}

Examples:
{knowledge.examples}

Notes:
{knowledge.notes}

Return ONLY valid JSON.
"""