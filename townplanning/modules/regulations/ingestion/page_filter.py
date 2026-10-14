"""
Page Filter.

Determines whether a page should be processed by the AI
pipeline or skipped.

This is a lightweight heuristic filter to avoid expensive
LLM calls on obvious non-regulation pages.
"""


class PageFilter:

    def should_process(
        self,
        page_number: int,
        text: str,
    ) -> tuple[bool, str]:

        text = text.strip()

        # ------------------------------------
        # Empty page
        # ------------------------------------

        if not text:

            return False, "Blank page"

        upper = text.upper()

        # ------------------------------------
        # Table of contents / Index
        # ------------------------------------

        toc_keywords = [

            "TABLE OF CONTENTS",
            "CONTENTS",
            "INDEX",

        ]

        if any(x in upper for x in toc_keywords):

            return False, "Table of Contents"

        # ------------------------------------
        # Very small pages
        # ------------------------------------

        if len(text.split()) < 20:

            return False, "Too little text"

        # ------------------------------------
        # Otherwise let GPT decide
        # ------------------------------------

        return True, "Candidate regulation page"
    

    SKIP_PAGE_TYPES = {
        "cover",
        "notification",
        "preface",
        "table_of_contents",
        "index",
        "appendix",
        "schedule",
        "form",
        "drawing",
        "blank",
        "other",
    }

    def should_skip(self, analysis):

        page_type = (
            analysis.page_type
            .lower()
            .strip()
        )

        return page_type in self.SKIP_PAGE_TYPES