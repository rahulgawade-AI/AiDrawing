"""
AI powered document analyzer.

Input:
    PageWindow

Output:
    PageAnalysis
"""

import json
from pathlib import Path

from townplanning.ai import AIRequest
#from townplanning.ai import OllamaClient
from townplanning.ai.factory import AIClientFactory

from townplanning.modules.regulations.ingestion.page_analysis import (
    PageAnalysis,
)


class DocumentAnalyzer:

    def __init__(self):

        #self.client = OllamaClient()
        self.client = AIClientFactory.create()

        prompt = Path(
            "townplanning/prompts/document_analysis.md"
        )

        self.system_prompt = prompt.read_text(
            encoding="utf-8"
        )

    # --------------------------------------------------

    def analyze(
        self,
        page_window,
    ) -> PageAnalysis:

        user_prompt = f"""
Previous Page

{page_window.previous_text}

------------------------------------------------

Current Page

{page_window.current_text}

------------------------------------------------

Next Page

{page_window.next_text}
"""

        response = self.client.generate(

            AIRequest(

                system_prompt=self.system_prompt,

                user_prompt=user_prompt,

                temperature=0.0,
            )

        )

        if not response.success:

            raise RuntimeError(
                response.error
            )
        # print("=" * 80)
        # print("DOCUMENT ANALYZER RESPONSE")
        # print("=" * 80)
        # print(response.content)
        # print("=" * 80)
        data = json.loads(
            response.content
        )

        #return PageAnalysis.model_validate(
        #    data
        #)
        return PageAnalysis(**data)