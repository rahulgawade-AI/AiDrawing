from dataclasses import dataclass


@dataclass(slots=True)
class RewrittenQuery:
    """
    Represents the rewritten version of a user's question.
    """

    original: str

    rewritten: str

    was_rewritten: bool = False