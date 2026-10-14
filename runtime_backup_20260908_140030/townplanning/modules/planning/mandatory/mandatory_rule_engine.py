from __future__ import annotations

import re
from typing import Any

from townplanning.infrastructure.database.models.rule_model import (
    RuleModel,
)

from townplanning.infrastructure.database.session import (
    SessionLocal,
)

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.rules.rule_condition_engine import (
    RuleConditionEngine,
)

from townplanning.modules.planning.mandatory.mandatory_constraint import (
    MandatoryConstraint,
    MandatoryConstraintResult,
)

from townplanning.modules.regulations.extraction.deterministic_regulatory_resolver import (
    DeterministicRegulatoryResolver,
)
class MandatoryRuleEngine:
    """
    Phase-1 deterministic mandatory building-design rule engine.

    Only rules capable of producing actual building-design
    constraints are considered.

    This engine:

        - uses PostgreSQL as the authoritative rule source
        - evaluates conditions deterministically
        - never invents regulatory values
        - never converts explanatory text into a verified value
        - never calculates missing regulations
        - never uses an LLM
        - may consume authoritative PostgreSQL source data selected
          upstream by Chroma -> OpenAI candidate selection

    Future fallback pipeline:

        deterministic rules
                |
                v
        unresolved mandatory constraint
                |
                v
             ChromaDB
                |
                v
             PostgreSQL
                |
                v
               PDF
                |
                v
             OpenAI
    """

    # ==========================================================
    # RESULT FIELD MAP
    # ==========================================================

    RESULT_FIELD_MAP = {

        # ------------------------------------------------------
        # FSI
        # ------------------------------------------------------

        "basic_permissible_fsi": "basic_fsi",
        "basic_fsi": "basic_fsi",

        "premium_fsi": "premium_fsi",

        "tdr_fsi": "tdr_fsi",

        "incentive_fsi": "incentive_fsi",

        "maximum_fsi": "maximum_fsi",
        "maximum_permissible_fsi": "maximum_fsi",
        "max_fsi": "maximum_fsi",

        "total_fsi": "total_fsi",

        # ------------------------------------------------------
        # COVERAGE
        # ------------------------------------------------------

        "maximum_ground_coverage":
            "maximum_ground_coverage",

        "maximumGroundCoverage":
            "maximum_ground_coverage",

        "ground_coverage":
            "maximum_ground_coverage",

        "groundCoverage":
            "maximum_ground_coverage",

        "maximum_coverage":
            "maximum_ground_coverage",

        "maximumCoverage":
            "maximum_ground_coverage",

        "coverage_percent":
            "maximum_ground_coverage",

        "ground_coverage_percent":
            "maximum_ground_coverage",

        # ------------------------------------------------------
        # SETBACKS
        # ------------------------------------------------------

        "front_margin":
            "front_setback",

        "front_setback":
            "front_setback",

        "rear_margin":
            "rear_setback",

        "rear_setback":
            "rear_setback",

        "side_margin":
            "side_setback",

        "side_setback":
            "side_setback",

        "side_margin_left":
            "side_setback_left",

        "side_setback_right":
            "side_setback_right",

        "left_setback":
            "side_setback_left",

        "right_setback":
            "side_setback_right",

        "side_rear_margins":
            "side_rear_margins",

        # ------------------------------------------------------
        # HEIGHT
        # ------------------------------------------------------

        "maximum_height":
            "maximum_height_m",

        "maximum_height_m":
            "maximum_height_m",

        "height_limit":
            "maximum_height_m",

        # ------------------------------------------------------
        # STOREYS
        # ------------------------------------------------------

        "maximum_storeys":
            "maximum_storeys",

        "max_storeys":
            "maximum_storeys",

        # ------------------------------------------------------
        # PARKING
        # ------------------------------------------------------

        "parking_required":
            "car_parking_required",

        "car_parking_required":
            "car_parking_required",

        "parking_requirement":
            "car_parking_required",

        "two_wheeler_parking_required":
            "two_wheeler_parking_required",

        "visitor_parking_required":
            "visitor_parking_required",

        "parking_area_required":
            "parking_area_required_m2",

        "parking_area_required_m2":
            "parking_area_required_m2",

        # ------------------------------------------------------
        # FIRE
        # ------------------------------------------------------

        "fire_access_required":
            "fire_access_required",

        "fire_lift_required":
            "fire_lift_required",

        "fire_staircase_required":
            "fire_staircase_required",

        "minimum_exit_count":
            "minimum_exit_count",

        "minimum_exit_width_m":
            "minimum_exit_width_m",

        # ------------------------------------------------------
        # CIRCULATION
        # ------------------------------------------------------

        "staircase_count":
            "staircase_count",

        "staircase_width":
            "staircase_width_m",

        "staircase_width_m":
            "staircase_width_m",

        "corridor_width":
            "corridor_width_m",

        "corridor_width_m":
            "corridor_width_m",

        # ------------------------------------------------------
        # LIFT
        # ------------------------------------------------------

        "lift_required":
            "lift_required",

        "lift_count":
            "lift_count",

        # ------------------------------------------------------
        # ACCESSIBILITY
        # ------------------------------------------------------

        "accessible_entrance_required":
            "accessible_entrance_required",

        "ramp_required":
            "ramp_required",

        "ramp_width":
            "ramp_width_m",

        "ramp_width_m":
            "ramp_width_m",

        "ramp_gradient":
            "ramp_gradient",

        # ------------------------------------------------------
        # OPEN / AMENITY
        # ------------------------------------------------------

        "minimum_open_space":
            "minimum_open_space_m2",

        "minimum_open_space_m2":
            "minimum_open_space_m2",

        "recreational_open_space_m2":
            "recreational_open_space_m2",

        "amenity_space_m2":
            "amenity_space_m2",

        # ------------------------------------------------------
        # SPECIAL CONDITIONS
        # ------------------------------------------------------

        "road_widening":
            "road_widening",

        "reservation_present":
            "reservation_present",
    }

    MANDATORY_RESULT_KEYS = frozenset(
        RESULT_FIELD_MAP.keys()
    )

    # ==========================================================
    # RESULT VALUES THAT ARE NOT ACTUAL CONSTRAINT VALUES
    # ==========================================================

    INFORMATIONAL_PATTERNS = (
        "refer to",
        "see clause",
        "see table",
        "as per",
        "subject to",
        "depending on",
        "depends on",
        "criteria",
        "criteria for",
        "calculation required",
        "to be calculated",
        "to be determined",
        "not specified",
        "not provided",
        "refer elsewhere",
        "refer to relevant",
    )

    # ==========================================================
    # CONSTRAINT KEYWORDS
    #
    # Used only as a SECONDARY filter.
    #
    # Result JSON containing an actual mapped constraint is
    # always the strongest signal.
    # ==========================================================

    MANDATORY_KEYWORDS = (
        "fsi",
        "floor space index",
        "building potential",

        "ground coverage",
        "coverage",

        "setback",
        "set back",
        "margin",
        "marginal distance",

        "building height",
        "height limit",

        "maximum storey",
        "maximum storeys",

        "parking",

        "fire access",
        "fire lift",
        "fire staircase",
        "exit width",
        "number of exit",

        "staircase",
        "stairway",
        "corridor",
        "lift",

        "accessible entrance",
        "accessibility",
        "ramp",

        "open space",
        "recreational open space",
        "amenity space",

        "road widening",
        "reservation",
    )

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(
        self,
        session_factory=SessionLocal,
    ) -> None:

        self.session_factory = (
            session_factory
        )

        self.condition_engine = (
            RuleConditionEngine()
        )

    # ==========================================================
    # PUBLIC API
    # ==========================================================

    def resolve(
        self,
        facts: PlanningFacts,
        *,
        selected_regulations: list[Any] | None = None,
        regulatory_sources: list[Any] | None = None,
        requested_fields: list[str] | None = None,
    ) -> MandatoryConstraintResult:
        """
        Resolve deterministic mandatory building-design constraints.

        Structured RuleModel data remains supported.  When the upstream
        Chroma -> OpenAI pipeline supplies selected regulation numbers and
        authoritative PostgreSQL regulation sources, those sources are also
        resolved by DeterministicRegulatoryResolver.

        No LLM is used here. No regulatory number is calculated or invented.
        """

        if facts is None:
            raise ValueError("PlanningFacts are required.")

        facts = facts.normalize()
        fact_values = self._fact_values(facts)
        result = MandatoryConstraintResult()

        # --------------------------------------------------------------
        # PATH 1: existing structured PostgreSQL RuleModel constraints.
        # --------------------------------------------------------------
        db = self.session_factory()

        try:
            rules = self._load_candidate_rules(db)

            # If upstream candidate selection is available, never evaluate
            # unrelated RuleModel rows.
            if selected_regulations:
                selected_numbers = {
                    self._canonical_regulation_number(item)
                    for item in selected_regulations
                }
                selected_numbers.discard(None)

                if selected_numbers:
                    rules = [
                        rule
                        for rule in rules
                        if self._rule_matches_selected_regulation(
                            rule,
                            selected_numbers,
                        )
                    ]

            for rule in rules:
                self._evaluate_rule(
                    rule,
                    fact_values,
                    result,
                )

        finally:
            db.close()

        # --------------------------------------------------------------
        # PATH 2: authoritative PostgreSQL source/table resolution.
        #
        # This is the bridge for rows such as regulation 6.3 where
        # result_json contains source_text/table content rather than
        # machine-readable result fields.
        # --------------------------------------------------------------
        if selected_regulations and regulatory_sources:
            deterministic_result = self._resolve_authoritative_sources(
                facts=facts,
                selected_regulations=selected_regulations,
                regulatory_sources=regulatory_sources,
                requested_fields=requested_fields,
            )

            self._merge_deterministic_result(
                deterministic_result,
                result,
            )

        return self._finalize(result)


 
# ==========================================================
    # ==========================================================
    # AUTHORITATIVE SOURCE RESOLUTION BRIDGE
    # ==========================================================

    @staticmethod
    def _canonical_regulation_number(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, dict):
            value = (
                value.get("regulation_number")
                or value.get("number")
                or value.get("regulation")
            )
        else:
            value = (
                getattr(value, "regulation_number", None)
                or getattr(value, "number", None)
                or getattr(value, "regulation", None)
                or value
            )

        text = str(value).strip()
        if not text:
            return None

        if text.upper().startswith("UDCPR:"):
            text = text.split(":", 1)[1].strip()

        return text.split("|", 1)[0].strip() or None

    @classmethod
    def _rule_matches_selected_regulation(
        cls,
        rule: RuleModel,
        selected_numbers: set[str],
    ) -> bool:
        """
        regulation_id is a UUID in this database.  The human regulation
        number is stored in metadata_json.number.
        """
        metadata = getattr(rule, "metadata_json", None)
        if not isinstance(metadata, dict):
            metadata = {}

        for candidate in (
            metadata.get("number"),
            metadata.get("regulation_number"),
            metadata.get("regulation"),
        ):
            number = cls._canonical_regulation_number(candidate)
            if number in selected_numbers:
                return True

        return False

    def _resolve_authoritative_sources(
        self,
        *,
        facts: PlanningFacts,
        selected_regulations: list[Any],
        regulatory_sources: list[Any],
        requested_fields: list[str] | None,
    ):
        resolver = DeterministicRegulatoryResolver()

        return resolver.resolve(
            facts=facts,
            selected_regulations=selected_regulations,
            sources=regulatory_sources,
            requested_fields=requested_fields or [],
        )

    @staticmethod
    def _merge_deterministic_result(
        deterministic_result: Any,
        output: MandatoryConstraintResult,
    ) -> None:
        """
        Promote only RESOLVED, provenance-bearing deterministic values.
        An unresolved source result is never converted to a fake value.
        """
        if deterministic_result is None:
            return

        status = getattr(deterministic_result, "status", None)
        constraints = getattr(
            deterministic_result,
            "constraints",
            [],
        )
        errors = getattr(
            deterministic_result,
            "errors",
            [],
        )

        if status not in {"RESOLVED", "PARTIAL"}:
            for error in errors:
                output.warnings.append(
                    "Authoritative source resolution: "
                    f"{error}"
                )
            return

        # PARTIAL means some fields are deterministically resolved while
        # another field/input remains unresolved. Promote only the verified
        # constraints that actually have provenance; never fabricate the
        # unresolved fields.
        for error in errors:
            output.warnings.append(
                "Authoritative source resolution: "
                f"{error}"
            )

        for item in constraints:
            if not isinstance(item, dict):
                continue

            key = item.get("field")
            value = item.get("value")

            if not key or value is None:
                continue

            output.constraints.append(
                MandatoryConstraint(
                    key=str(key),
                    value=value,
                    unit=item.get("unit"),
                    source_rule_id=(
                        str(item.get("source_id"))
                        if item.get("source_id") is not None
                        else "postgresql-source"
                    ),
                    regulation_id=(
                        str(item.get("regulation_number"))
                        if item.get("regulation_number") is not None
                        else "source-resolution"
                    ),
                    rule_name=(
                        "Regulation "
                        f"{item.get('regulation_number') or 'unknown'}"
                    ),
                    category="regulatory_source",
                    priority=0,
                    status="verified",
                    reason=(
                        "Constraint resolved deterministically from "
                        "authoritative PostgreSQL regulation source."
                    ),
                    metadata={
                        "resolution_path": "postgresql_source",
                        "source_id": item.get("source_id"),
                        "condition": item.get("condition", {}),
                        "confidence": item.get(
                            "confidence",
                            "authoritative",
                        ),
                    },
                )
            )

        # A source resolver must provide provenance for every promoted
        # value.  Do not silently promote an untraceable values dictionary.
        if getattr(deterministic_result, "values", {}) and not constraints:
            output.warnings.append(
                "Authoritative source resolver returned values without "
                "constraint provenance; values were not promoted."
            )

# RULE APPLICABILITY
# ==========================================================

    def diagnose_rule_applicability(
        self,
        facts: PlanningFacts,
    ) -> list[dict[str, Any]]:
        """
        Diagnostic view of rule applicability.

        This is intentionally read-only.  It is useful for finding rules
        whose PostgreSQL applicability metadata is missing or malformed.
        """
        facts = facts.normalize()
        fact_values = self._fact_values(facts)
        db = self.session_factory()

        rows: list[dict[str, Any]] = []
        try:
            for rule in self._load_candidate_rules(db):
                status, reason = self._classify_rule_applicability(
                    rule,
                    fact_values,
                )
                rows.append(
                    {
                        "rule_id": str(rule.id),
                        "regulation_id": (
                            str(rule.regulation_id)
                            if rule.regulation_id is not None
                            else None
                        ),
                        "rule_name": rule.name,
                        "status": status,
                        "reason": reason,
                        "condition_json": rule.condition_json,
                    }
                )
        finally:
            db.close()

        return rows

    def _classify_rule_applicability(
        self,
        rule: RuleModel,
        facts: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Resolve applicability using ONLY structured persisted metadata.

        Priority:

            1. metadata_json["applicability"]
            2. condition_json

        Empty condition_json is NOT automatically unconditional.

        A rule without explicit machine-readable applicability metadata is
        unresolved.  This prevents scoped regulatory rules from being
        incorrectly applied to every project.
        """

        metadata = getattr(rule, "metadata_json", None)

        if not isinstance(metadata, dict):
            metadata = {}

        # --------------------------------------------------------------
        # Preferred applicability location
        # --------------------------------------------------------------

        applicability = metadata.get("applicability")

        if applicability is not None:
            if not isinstance(applicability, dict):
                return (
                    "unresolved",
                    "metadata_json.applicability is not a valid object.",
                )

            return self._classify_condition(
                applicability,
                facts,
            )

        # --------------------------------------------------------------
        # Legacy / primary condition_json
        # --------------------------------------------------------------

        condition = getattr(rule, "condition_json", None)

        if isinstance(condition, dict) and condition:
            return self._classify_condition(
                condition,
                facts,
            )

        # --------------------------------------------------------------
        # No machine-readable applicability
        # --------------------------------------------------------------

        return (
            "unresolved",
            "Rule has no explicit machine-readable applicability "
            "condition. condition_json is empty and "
            "metadata_json.applicability is missing.",
        )


    def _classify_condition(
        self,
        node: Any,
        facts: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Recursively classify a persisted rule condition.

        Handles:

            AND
            OR
            field/operator/value
            typed conditions
            semantic conditions
        """

        if not isinstance(node, dict):

            return (
                "unresolved",
                "Unsupported condition structure.",
            )

        condition_type = str(
            node.get("type", "")
        ).strip().lower()

        # ======================================================
        # AND
        # ======================================================

        if condition_type == "and":

            clauses = node.get(
                "clauses",
                node.get(
                    "conditions",
                    [],
                ),
            )

            if not isinstance(
                clauses,
                list,
            ):

                return (
                    "unresolved",
                    "AND condition has invalid clauses.",
                )

            unresolved = []

            for clause in clauses:

                status, reason = (
                    self._classify_condition(
                        clause,
                        facts,
                    )
                )

                # One definite FALSE condition makes
                # the entire AND rule not applicable.
                if status == "not_applicable":

                    return (
                        "not_applicable",
                        reason,
                    )

                if status == "unresolved":

                    unresolved.append(
                        reason
                    )

            if unresolved:

                return (
                    "unresolved",
                    "; ".join(
                        unresolved
                    ),
                )

            return (
                "applicable",
                "All AND conditions satisfied.",
            )

        # ======================================================
        # OR
        # ======================================================

        if condition_type == "or":

            clauses = node.get(
                "clauses",
                node.get(
                    "conditions",
                    [],
                ),
            )

            if not isinstance(
                clauses,
                list,
            ):

                return (
                    "unresolved",
                    "OR condition has invalid clauses.",
                )

            unresolved = []

            for clause in clauses:

                status, reason = (
                    self._classify_condition(
                        clause,
                        facts,
                    )
                )

                # One definite TRUE condition is sufficient.
                if status == "applicable":

                    return (
                        "applicable",
                        reason,
                    )

                if status == "unresolved":

                    unresolved.append(
                        reason
                    )

            if unresolved:

                return (
                    "unresolved",
                    "; ".join(
                        unresolved
                    ),
                )

            return (
                "not_applicable",
                "No OR condition matched.",
            )

        # ======================================================
        # FIELD CONDITION
        # ======================================================

        if "field" in node:

            field = node.get(
                "field"
            )

            # Prevent the old:
            #
            # TypeError: unhashable type: 'list'
            #
            if isinstance(
                field,
                list,
            ):

                return self._classify_list_field_condition(
                    node,
                    facts,
                )

            if not isinstance(
                field,
                str,
            ):

                return (
                    "unresolved",
                    "Condition field is invalid.",
                )

            actual = (
                self.condition_engine._get_fact(
                    facts,
                    field,
                )
            )

            # Fact does not exist.
            #
            # Do NOT invent a value.
            if actual is None:

                return (
                    "unresolved",
                    f"Missing fact: {field}",
                )

            try:

                condition_result = (
                    self.condition_engine.evaluate(
                        node,
                        facts,
                    )
                )

            except Exception as exc:

                return (
                    "unresolved",
                    (
                        f"Condition evaluation failed "
                        f"for {field}: {exc}"
                    ),
                )

            status = getattr(
                condition_result,
                "status",
                None,
            )

            reason = getattr(
                condition_result,
                "reason",
                "",
            )

            if status == "applicable":

                return (
                    "applicable",
                    reason,
                )

            if status == "not_applicable":

                return (
                    "not_applicable",
                    reason,
                )

            return (
                "unresolved",
                reason or f"Unable to evaluate {field}.",
            )

    # ======================================================
    # SEMANTIC CONDITION
    # ======================================================

        return self._classify_semantic_condition(
        node,
        facts,
    )

    # ==========================================================
    # RULE DISCOVERY
    # ==========================================================

    def _load_candidate_rules(
        self,
        db,
    ) -> list[RuleModel]:
        """
        Reduce the complete PostgreSQL rule universe.

        Priority:

            1. result_json contains an actual mandatory
               constraint field
            2. rule metadata strongly indicates a mandatory
               building constraint

        Informational-only result objects are rejected.
        """

        rules = (
            db.query(RuleModel)
            .filter(
                RuleModel.enabled.is_(True)
            )
            .order_by(
                RuleModel.priority.asc()
            )
            .all()
        )

        candidates: list[
            RuleModel
        ] = []

        for rule in rules:

            if self._looks_like_mandatory_rule(
                rule
            ):
                candidates.append(
                    rule
                )

        return candidates

    
    def _looks_like_mandatory_rule(
        self,
        rule: RuleModel,
    ) -> bool:
        """
        Return True only when result_json contains a recognized
        mandatory building-design constraint with a concrete value.

        The rule name/category alone is NOT enough.  This prevents
        explanatory rules such as "refer to Table 6-G" from becoming
        verified constraints.
        """

        result = rule.result_json or {}

        if not isinstance(result, dict):
            return False

        for raw_key, raw_value in result.items():

            mapped_key = self._map_result_key(raw_key)

            if mapped_key is None:
                continue

            if self._is_actual_constraint_value(raw_value):
                return True

        return False


# VALUE CLASSIFICATION
    # ==========================================================

    @classmethod
    def _is_actual_constraint_value(
        cls,
        value: Any,
    ) -> bool:
        """
        Determine whether a persisted result represents an actual
        regulatory constraint.

        Important:

        A constraint may be represented as:

            2.5
            3
            True / False
            "1:12"
            "1800mm"

        or as a structured object:

            {"value": 4.5, "unit": "m"}

        Some valid UDCPR constraints use structured objects without
        a "value" key, for example:

            {
                "ground_floor": True,
                "additional_floors": 1
            }

        Such objects are valid constraint payloads and must not be
        rejected merely because they do not contain "value".

        Informational/explanatory text is never accepted.
        """

        if value is None:
            return False

        # ------------------------------------------------------
        # Boolean regulatory values
        # ------------------------------------------------------

        if isinstance(value, bool):
            return True

        # ------------------------------------------------------
        # Numeric regulatory values
        # ------------------------------------------------------

        if isinstance(value, (int, float)):
            return True

        # ------------------------------------------------------
        # Structured regulatory values
        # ------------------------------------------------------

        if isinstance(value, dict):

            if not value:
                return False

            # Explicit value object.
            if "value" in value:
                return cls._is_actual_constraint_value(
                    value.get("value")
                )

            # Quantity object.
            if "quantity" in value:
                return cls._is_actual_constraint_value(
                    value.get("quantity")
                )

            # Some legitimate constraints are structured
            # dictionaries without a "value" field.
            #
            # Example:
            # {
            #     "ground_floor": True,
            #     "additional_floors": 1
            # }
            #
            # Accept only dictionaries whose contents contain
            # concrete scalar/structured regulatory values.
            for key, item in value.items():

                if key in {
                    "note",
                    "description",
                    "reference",
                    "source",
                    "action",
                    "message",
                }:
                    continue

                if cls._is_actual_constraint_value(item):
                    return True

            return False

        # ------------------------------------------------------
        # String regulatory values
        # ------------------------------------------------------

        if isinstance(value, str):

            text = value.strip()

            if not text:
                return False

            if cls._is_informational_text(text):
                return False

            # Ratio, e.g. 1:12
            if re.fullmatch(
                r"\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?",
                text,
            ):
                return True

            # Numeric value with optional unit.
            #
            # Examples:
            #   1800mm
            #   4.5 m
            #   2.5 FSI
            #   15 feet
            if re.search(
                r"\d",
                text,
            ):
                return True

            # Explicit yes/no values can represent mandatory
            # requirements.
            if text.lower() in {
                "yes",
                "no",
                "required",
                "not required",
                "mandatory",
            }:
                return True

            return False

        return False

    @classmethod
    def _is_informational_text(
        cls,
        value: str,
    ) -> bool:

        normalized = (
            value.strip()
            .lower()
        )

        return any(
            pattern in normalized
            for pattern
            in cls.INFORMATIONAL_PATTERNS
        )

    @classmethod
    def _result_is_informational(
        cls,
        result: Any,
    ) -> bool:

        if not isinstance(
            result,
            dict,
        ):
            return True

        actual_constraint_found = False

        for raw_key, raw_value in (
            result.items()
        ):

            mapped = (
                cls._map_result_key(
                    raw_key
                )
            )

            if mapped is None:
                continue

            if cls._is_actual_constraint_value(
                raw_value
            ):
                actual_constraint_found = True

        return not actual_constraint_found

    # ==========================================================
    # FACTS
    # ==========================================================

    @staticmethod
    def _fact_values(
        facts: PlanningFacts,
    ) -> dict[str, Any]:

        if hasattr(
            facts,
            "to_dict",
        ):

            values = dict(
                facts.to_dict()
            )

        else:

            values = dict(
                vars(facts)
            )

        aliases = {
            "buildingType":
                "building_type",

            "buildingUse":
                "building_use",

            "useType":
                "building_use",

            "occupancy_type":
                "building_use",

            "occupancyType":
                "building_use",

            "roadWidth":
                "road_width",

            "plotArea":
                "plot_area",

            "plotNumber":
                "plot_number",

            "cityName":
                "city",

            "districtName":
                "district",
        }

        for alias, canonical in (
            aliases.items()
        ):

            if (
                canonical in values
                and values[canonical]
                is not None
            ):

                values.setdefault(
                    alias,
                    values[canonical],
                )

        return values

    # ==========================================================
    # RULE EVALUATION
    # ==========================================================

    def _evaluate_rule(
        self,
        rule: RuleModel,
        facts: dict[str, Any],
        output: MandatoryConstraintResult,
    ) -> None:

        # --------------------------------------------------------------
        # Resolve applicability through the authoritative classifier.
        # --------------------------------------------------------------

        applicability, applicability_reason = (
            self._classify_rule_applicability(
                rule,
                facts,
            )
        )

        # --------------------------------------------------------------
        # NOT APPLICABLE
        # --------------------------------------------------------------

        if applicability == "not_applicable":

            output.not_applicable_rule_ids.append(
                str(rule.id)
            )

            return

        # --------------------------------------------------------------
        # UNRESOLVED
        # --------------------------------------------------------------

        if applicability == "unresolved":

            output.unresolved_rule_ids.append(
                str(rule.id)
            )

            output.warnings.append(
                f"Rule {rule.id} applicability unresolved: "
                f"{applicability_reason}"
            )

            return

        # --------------------------------------------------------------
        # INVALID STATE
        # --------------------------------------------------------------

        if applicability != "applicable":

            output.unresolved_rule_ids.append(
                str(rule.id)
            )

            output.warnings.append(
                f"Rule {rule.id} returned invalid applicability "
                f"state: {applicability!r}"
            )

            return

        # --------------------------------------------------------------
        # APPLICABLE
        # --------------------------------------------------------------

        result_json = rule.result_json or {}

        constraints = self._extract_constraints(
            rule,
            result_json,
        )

        if not constraints:
            return

        output.applicable_rule_ids.append(
            str(rule.id)
        )

        output.constraints.extend(
            constraints
        )
        # ==========================================================
        # CONSTRAINT EXTRACTION
        # ==========================================================

    def _extract_constraints(
        self,
        rule: RuleModel,
        result: dict[str, Any],
    ) -> list[MandatoryConstraint]:

        constraints: list[
            MandatoryConstraint
        ] = []

        if not isinstance(
            result,
            dict,
        ):
            return constraints

        for raw_key, raw_value in (
            result.items()
        ):

            mapped_key = (
                self._map_result_key(
                    raw_key
                )
            )

            if mapped_key is None:
                continue

            # --------------------------------------------------
            # Never treat explanatory text as a verified value.
            # --------------------------------------------------

            if not self._is_actual_constraint_value(
                raw_value
            ):

                continue

            value, unit = (
                self._extract_value_unit(
                    raw_value
                )
            )

            if value is None:
                continue

            # --------------------------------------------------
            # Normalize simple measurements.
            # --------------------------------------------------

            value, unit = (
                self._normalize_constraint_value(
                    value,
                    unit,
                )
            )

            constraints.append(
                MandatoryConstraint(
                    key=mapped_key,
                    value=value,
                    unit=unit,
                    source_rule_id=str(
                        rule.id
                    ),
                    regulation_id=str(
                        rule.regulation_id
                    ),
                    rule_name=rule.name,
                    category=rule.category,
                    priority=rule.priority,
                    status="verified",
                    reason=(
                        "Constraint extracted from "
                        "applicable PostgreSQL rule."
                    ),
                    metadata={
                        "result_key": raw_key,

                        "raw_value": raw_value,

                        "description": (
                            getattr(
                                rule,
                                "description",
                                None,
                            )
                        ),
                    },
                )
            )

        return constraints

    # ==========================================================
    # RESULT KEY NORMALIZATION
    # ==========================================================

    @classmethod
    def _map_result_key(
        cls,
        raw_key: Any,
    ) -> str | None:

        key = str(
            raw_key
        ).strip()

        if key in cls.RESULT_FIELD_MAP:
            return cls.RESULT_FIELD_MAP[key]

        normalized = (
            key.lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        for source, target in (
            cls.RESULT_FIELD_MAP.items()
        ):

            source_normalized = (
                source.lower()
                .replace("-", "_")
                .replace(" ", "_")
            )

            if normalized == source_normalized:
                return target

        return None

    # ==========================================================
    # VALUE EXTRACTION
    # ==========================================================

    @staticmethod
    def _extract_value_unit(
        value: Any,
    ) -> tuple[Any | None, str | None]:

        if value is None:
            return None, None

        if isinstance(
            value,
            dict,
        ):

            if "value" not in value:
                return None, None

            return (
                value.get("value"),
                value.get("unit"),
            )

        return value, None

    # ==========================================================
    # VALUE NORMALIZATION
    # ==========================================================

    @staticmethod
    def _normalize_constraint_value(
        value: Any,
        unit: str | None,
    ) -> tuple[Any, str | None]:
        """
        Normalize simple dimensional strings.

        Example:

            1800mm -> 1.8 m

        Ratios such as:

            1:12

        remain strings.
        """

        if not isinstance(
            value,
            str,
        ):
            return value, unit

        text = value.strip()

        # ------------------------------------------------------
        # Already supplied unit.
        # ------------------------------------------------------

        if unit:
            normalized_unit = (
                str(unit)
                .strip()
                .lower()
            )

            # mm -> m
            if normalized_unit in {
                "mm",
                "millimeter",
                "millimeters",
            }:

                try:
                    numeric = float(
                        text
                    )

                    return (
                        numeric / 1000.0,
                        "m",
                    )

                except ValueError:
                    pass

            return value, unit

        # ------------------------------------------------------
        # Inline millimetres.
        #
        # 1800mm -> 1.8 m
        # ------------------------------------------------------

        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*mm\s*",
            text,
            flags=re.IGNORECASE,
        )

        if match:

            return (
                float(
                    match.group(1)
                ) / 1000.0,
                "m",
            )

        # ------------------------------------------------------
        # Inline centimetres.
        # ------------------------------------------------------

        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*cm\s*",
            text,
            flags=re.IGNORECASE,
        )

        if match:

            return (
                float(
                    match.group(1)
                ) / 100.0,
                "m",
            )

        # ------------------------------------------------------
        # Inline metres.
        # ------------------------------------------------------

        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*m\s*",
            text,
            flags=re.IGNORECASE,
        )

        if match:

            return (
                float(
                    match.group(1)
                ),
                "m",
            )

        # ------------------------------------------------------
        # Ratio.
        # ------------------------------------------------------

        if re.fullmatch(
            r"\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?",
            text,
        ):

            return text, None

        return value, unit

    # ==========================================================
    # FINALIZATION
    # ==========================================================

    def _finalize(
        self,
        result: MandatoryConstraintResult,
    ) -> MandatoryConstraintResult:
        """
        Resolve duplicate constraints deterministically.

        Lower priority wins only when the values agree.

        Conflicting authoritative values remain unresolved.
        """

        grouped: dict[
            str,
            list[MandatoryConstraint],
        ] = {}

        for constraint in (
            result.constraints
        ):

            grouped.setdefault(
                constraint.key,
                [],
            ).append(
                constraint
            )

        final_constraints: list[
            MandatoryConstraint
        ] = []

        for key, candidates in (
            grouped.items()
        ):

            candidates.sort(
                key=lambda item: (
                    item.priority,
                    item.source_rule_id,
                )
            )

            selected = candidates[0]

            distinct_values = {
                (
                    str(item.value),
                    str(item.unit),
                )
                for item in candidates
            }

            if len(
                distinct_values
            ) > 1:

                result.warnings.append(
                    "Conflicting mandatory values "
                    f"for {key}: "
                    + ", ".join(
                        sorted(
                            f"{value} "
                            f"{unit or ''}".strip()
                            for value, unit
                            in distinct_values
                        )
                    )
                )

                selected = MandatoryConstraint(
                    key=key,
                    value=None,
                    unit=None,
                    source_rule_id=(
                        selected.source_rule_id
                    ),
                    regulation_id=(
                        selected.regulation_id
                    ),
                    rule_name=(
                        selected.rule_name
                    ),
                    category=(
                        selected.category
                    ),
                    priority=(
                        selected.priority
                    ),
                    status="unresolved",
                    reason=(
                        "Multiple applicable rules "
                        "provide conflicting values."
                    ),
                    metadata={
                        "candidate_values": [
                            {
                                "value": item.value,
                                "unit": item.unit,
                                "rule_id": (
                                    item.source_rule_id
                                ),
                            }
                            for item in candidates
                        ]
                    },
                )

            final_constraints.append(
                selected
            )

        result.constraints = sorted(
            final_constraints,
            key=lambda item: (
                item.key,
                item.priority,
            ),
        )

        return result

    def _classify_list_field_condition(
        self,
        node: dict[str, Any],
        facts: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Handle conditions where field itself is a list.

        Example:

            {
                "type": "presence",
                "field": [
                    "development plan",
                    "approved layout"
                ],
                "operator": "any"
            }

        These are semantic conditions and cannot be passed
        directly into RuleConditionEngine._get_fact().
        """

        fields = node.get(
            "field"
        )

        if not isinstance(
            fields,
            list,
        ):

            return (
                "unresolved",
                "Invalid list-field condition.",
            )

        operator = str(
            node.get(
                "operator",
                "any",
            )
        ).strip().lower()

        present = []

        for field in fields:

            if not isinstance(
                field,
                str,
            ):
                continue

            value = (
                self.condition_engine._get_fact(
                    facts,
                    field,
                )
            )

            if value is not None:

                present.append(
                    field
                )

        # ------------------------------------------------------
        # ANY
        # ------------------------------------------------------

        if operator == "any":

            if present:

                return (
                    "applicable",
                    (
                        "At least one required "
                        f"field is present: {present}"
                    ),
                )

            return (
                "unresolved",
                (
                    "None of the semantic fields "
                    f"are available: {fields}"
                ),
            )

        # ------------------------------------------------------
        # ALL
        # ------------------------------------------------------

        if operator == "all":

            if len(present) == len(fields):

                return (
                    "applicable",
                    "All semantic fields are present.",
                )

            return (
                "unresolved",
                (
                    "Missing semantic fields: "
                    f"{[f for f in fields if f not in present]}"
                ),
            )

        return (
            "unresolved",
            (
                f"Unsupported list-field operator: "
                f"{operator}"
            ),
        )

    def _classify_semantic_condition(
        self,
        node: dict[str, Any],
        facts: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Handle simple semantic rule conditions such as:

            {
                "building_type": "Residential"
            }

            {
                "zone_type": "TOD"
            }

            {
                "roof_type": "flat"
            }

        No missing value is invented.
        """

        checked = False

        for field, expected in node.items():

            if field in {
                "type",
                "operator",
                "value",
                "values",
                "clauses",
                "conditions",
            }:
                continue

            checked = True

            actual = (
                self.condition_engine._get_fact(
                    facts,
                    field,
                )
            )

            if actual is None:

                return (
                    "unresolved",
                    f"Missing fact: {field}",
                )

            expected_values = (
                expected
                if isinstance(
                    expected,
                    list,
                )
                else [expected]
            )

            actual_text = str(
                actual
            ).strip().lower()

            expected_text = [
                str(value)
                .strip()
                .lower()
                for value in expected_values
            ]

            # "any" means no restriction.
            if "any" in expected_text:

                continue

            if actual_text not in expected_text:

                return (
                    "not_applicable",
                    (
                        f"{field}={actual!r} "
                        f"does not match "
                        f"{expected!r}."
                    ),
                )

        if checked:

            return (
                "applicable",
                "Semantic conditions matched.",
            )

        return (
            "unresolved",
            "No evaluable condition fields found.",
        )