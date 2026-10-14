from __future__ import annotations

import re

from townplanning.modules.query.dom.query_intent import (
    QueryIntent,
)


class IntentDetectionService:
    """
    Detect the intent of a user query.

    Uses deterministic rules for speed,
    explainability and reproducibility.
    """

    DEFINITION_PATTERNS = [
        r"\bwhat\s+is\b",
        r"\bdefine\b",
        r"\bmeaning\b",
        r"\bexplain\b",
    ]

    REGULATION_PATTERNS = [
        r"\brule\b",
        r"\bregulation\b",
        r"\bclause\b",
        r"\bsection\b",
        r"\bchapter\b",
        r"\btable\b",
        r"\bappendix\b",
        r"\bannexure\b",
        r"\b\d+\.\d+(\.\d+)*\b",
    ]

    CONSTRAINT_PATTERNS = [
        r"\bmaximum\b",
        r"\bminimum\b",
        r"\bpermissible\b",
        r"\blimit\b",
        r"\ballowed\b",
        r"\brequired\b",
        r"\bheight\b",
        r"\bfsi\b",
        r"\bsetback\b",
        r"\bcoverage\b",
    ]

    PROCEDURE_PATTERNS = [
        r"\bhow\b",
        r"\bprocess\b",
        r"\bprocedure\b",
        r"\bsteps\b",
        r"\bapproval\b",
        r"\bpermission\b",
        r"\bcertificate\b",
    ]

    ELIGIBILITY_PATTERNS = [
        r"\beligible\b",
        r"\beligibility\b",
        r"\bqualify\b",
        r"\bcan i\b",
        r"\bwho can\b",
    ]

    COMPARISON_PATTERNS = [
        r"\bcompare\b",
        r"\bdifference\b",
        r"\bversus\b",
        r"\bvs\b",
    ]

    CALCULATION_PATTERNS = [
        r"\bcalculate\b",
        r"\bcalculation\b",
        r"\bcompute\b",
        r"\bformula\b",
    ]

    EXCEPTION_PATTERNS = [
        r"\bexception\b",
        r"\bexemption\b",
        r"\brelaxation\b",
        r"\bexcluded\b",
    ]

    TABLE_PATTERNS = [
        r"\btable\b",
        r"\bschedule\b",
        r"\bchart\b",
    ]

    def detect(
        self,
        question: str,
    ) -> QueryIntent:
        """
        Detect the most likely intent.
        """

        query = question.lower().strip()

        if self._matches(self.DEFINITION_PATTERNS, query):
            return QueryIntent.DEFINITION

        if self._matches(self.REGULATION_PATTERNS, query):
            return QueryIntent.REGULATION_LOOKUP

        if self._matches(self.TABLE_PATTERNS, query):
            return QueryIntent.TABLE_LOOKUP

        if self._matches(self.CONSTRAINT_PATTERNS, query):
            return QueryIntent.CONSTRAINT

        if self._matches(self.PROCEDURE_PATTERNS, query):
            return QueryIntent.PROCEDURE

        if self._matches(self.ELIGIBILITY_PATTERNS, query):
            return QueryIntent.ELIGIBILITY

        if self._matches(self.COMPARISON_PATTERNS, query):
            return QueryIntent.COMPARISON

        if self._matches(self.CALCULATION_PATTERNS, query):
            return QueryIntent.CALCULATION

        if self._matches(self.EXCEPTION_PATTERNS, query):
            return QueryIntent.EXCEPTION

        return QueryIntent.GENERAL

    @staticmethod
    def _matches(
        patterns: list[str],
        query: str,
    ) -> bool:

        return any(
            re.search(pattern, query)
            for pattern in patterns
        )