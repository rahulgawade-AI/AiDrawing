from __future__ import annotations

from enum import Enum


class QueryIntent(str, Enum):
    """
    Supported query intents.
    """

    UNKNOWN = "unknown"

    DEFINITION = "definition"

    REGULATION_LOOKUP = "regulation_lookup"

    CONSTRAINT = "constraint"

    COMPARISON = "comparison"

    PROCEDURE = "procedure"

    ELIGIBILITY = "eligibility"

    CALCULATION = "calculation"

    EXCEPTION = "exception"

    TABLE_LOOKUP = "table_lookup"

    GENERAL = "general"