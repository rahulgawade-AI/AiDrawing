"""
Validates extracted Regulation objects before
they are persisted to the database.
"""

from townplanning.validation.validation_result import (
    ValidationResult,
)


class RegulationValidator:

    def validate(

        self,

        regulation,

        knowledge,

        rules,

    ) -> ValidationResult:

        result = ValidationResult()

        # ---------------------------------
        # Regulation
        # ---------------------------------

        if not regulation.number:

            result.add_error(
                "Missing regulation number."
            )

        if not regulation.title:

            result.add_error(
                "Missing regulation title."
            )

        # ---------------------------------
        # Knowledge
        # ---------------------------------

        if not knowledge.title:

            result.add_error(
                "Knowledge title missing."
            )

        if not knowledge.summary:

            result.add_error(
                "Knowledge summary missing."
            )

        if not knowledge.purpose:

            result.add_warning(
                "Purpose missing."
            )

        # ---------------------------------
        # Measurements
        # ---------------------------------

        if not knowledge.measurements:

            result.add_warning(
                "No measurements extracted."
            )

        # ---------------------------------
        # References
        # ---------------------------------

        if not knowledge.references:

            result.add_warning(
                "No references extracted."
            )

        # ---------------------------------
        # Rules
        # ---------------------------------

        if len(rules) == 0:

            result.add_error(
                "No rules extracted."
            )

        # ---------------------------------
        # Statistics
        # ---------------------------------

        result.statistics = {

            "rules": len(rules),

            "measurements": len(
                knowledge.measurements
            ),

            "references": len(
                knowledge.references
            ),
        }

        return result