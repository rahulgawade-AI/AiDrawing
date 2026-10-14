from __future__ import annotations

from typing import Any

from townplanning.modules.planning.domain.planning_facts import PlanningFacts
from townplanning.modules.planning.domain.planning_constraints import PlanningConstraints
from townplanning.modules.planning.regulations.udcpr_rule_resolver import UDCPRRuleResolver
from townplanning.modules.planning.mandatory.mandatory_rule_engine import MandatoryRuleEngine
from townplanning.modules.regulations.extraction.regulatory_context_retriever import RegulatoryContextRetriever
from townplanning.modules.planning.regulations.constraint_calculator import ConstraintCalculator
from townplanning.infrastructure.database.session import SessionLocal

from townplanning.infrastructure.database.repositories import (
    SQLAlchemyTableRepository,
)

class PlanningService:
    """Main deterministic entry point for the UDCPR planning engine.

    The service deliberately separates:

    * raw/canonical planning facts; and
    * derived regulatory facts produced by deterministic calculation.

    This is important because UDCPR rules can depend on values calculated
    by earlier rules (for example ``calculated_fsi`` versus a Table 6-G
    building potential).  Raw PlanningFacts are never mutated to satisfy
    such rules.
    """

    def __init__(self):
        self.rule_resolver = UDCPRRuleResolver()
        self.table_session = SessionLocal()

        self.table_repository = SQLAlchemyTableRepository(
            self.table_session
        )

        self.constraint_calculator = ConstraintCalculator(
            table_repository=self.table_repository
        )

    @staticmethod
    def _regulatory_query(
        facts: PlanningFacts,
        requested_fields: list[str],
    ) -> str:
        """Build semantic retrieval context only; never calculate a value."""
        parts = [
            "Determine applicable regulatory table rows and conditional values.",
            "Do not calculate or invent values; use authoritative PostgreSQL source tables.",
        ]
        for key in (
            "city", "district", "planning_authority", "municipality",
            "zone", "zone_type", "land_use_zone",
            "building_use", "building_type", "congested_area",
            "group_housing", "road_width", "plot_area",
            "tenement_carpet_area", "building_height", "requested_height",
            "requested_floors", "development_type", "special_building",
        ):
            value = getattr(facts, key, None)
            if value is not None:
                parts.append(f"{key}={value}")
        parts.append("requested_fields=" + ",".join(requested_fields))
        return " | ".join(parts)

    @staticmethod
    def _derived_facts(
        facts: PlanningFacts,
        constraints: PlanningConstraints,
    ) -> dict[str, Any]:
        """Build deterministic facts needed by dependent UDCPR rules.

        ``calculated_fsi`` here intentionally means the FSI already
        established before a premium/additional-FSI permission is granted.
        Premium FSI is therefore not circularly used to prove its own
        eligibility.
        """
        base_components = [
            constraints.basic_fsi,
            constraints.tdr_fsi,
            constraints.incentive_fsi,
        ]
        calculated_fsi = PlanningService._sum_numeric_components(
            base_components
        )

        derived: dict[str, Any] = {
            "basic_fsi": constraints.basic_fsi,
            "calculated_fsi": calculated_fsi,
            "maximum_fsi": constraints.maximum_fsi,
            "maximum_building_potential_table_6g": constraints.maximum_fsi,
        }

        if facts.plot_area is not None:
            derived["plot_area_for_fsi"] = facts.plot_area

        # A proposed/requested height or a requested floor count is a valid
        # derived input for threshold rules (fire lift, refuge area, road
        # width checks, etc.).  It is deliberately NOT treated as a maximum
        # permissible height.
        proposed_height = facts.building_height
        if proposed_height is None:
            proposed_height = facts.requested_height
        if proposed_height is None and facts.requested_floors is not None and facts.floor_height is not None:
            proposed_height = facts.requested_floors * facts.floor_height
        if proposed_height is not None:
            derived["building_height"] = proposed_height
            derived["proposed_building_height"] = proposed_height

        if facts.requested_floors is not None:
            derived["number_of_floors"] = facts.requested_floors

        # Remove unknown/None derived values so a missing value remains
        # genuinely unresolved in the condition engine.
        return {key: value for key, value in derived.items() if value is not None}

    @staticmethod
    def _numeric_component(value: Any) -> float | int | None:
        """Return a numeric planning component without parsing arbitrary text.

        Regulatory values normally arrive as numbers, but the deterministic
        resolver/constraint model may preserve a scalar as a numeric string.
        Only a complete scalar numeric string is accepted here; prose is never
        scanned for numbers.
        """
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            text = value.strip()
            if text and __import__("re").fullmatch(
                r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text
            ):
                number = float(text)
                return int(number) if number.is_integer() else number
        return None

    @classmethod
    def _sum_numeric_components(cls, values: list[Any]) -> float | int | None:
        """Sum only scalar numeric components; ignore unresolved values."""
        normalized = [cls._numeric_component(v) for v in values]
        known = [v for v in normalized if v is not None]
        if not known:
            return None
        total = sum(known)
        return int(total) if isinstance(total, float) and total.is_integer() else total

    @staticmethod
    def _merge_rules(
        first: list,
        second: list,
    ) -> list:
        """Prefer the latest evaluation for each database rule."""
        merged = {str(rule.rule_id): rule for rule in first}
        for rule in second:
            merged[str(rule.rule_id)] = rule
        return list(merged.values())

    def evaluate(self, facts: PlanningFacts) -> PlanningConstraints:
        """Evaluate the authoritative regulatory state for ``facts``.

        The public PlanningService is the single production entry point.
        It does NOT run the legacy ``UDCPRRuleResolver -> ConstraintCalculator``
        path first, because that path can treat source/table rows with empty
        conditions as unconditional.

        Instead the mandatory engine owns the regulatory pipeline:

            Chroma semantic retrieval
                -> OpenAI candidate selection
                -> PostgreSQL authoritative source
                -> deterministic applicability/table resolution
                -> PlanningConstraints

        OpenAI never calculates a regulatory value.  The returned values are
        copied from the deterministic mandatory result only.
        """
        if facts is None:
            raise ValueError("PlanningFacts are required.")

        requested_fields = [
            "basic_fsi", "premium_fsi", "tdr_fsi", "incentive_fsi",
            "maximum_fsi", "total_fsi", "maximum_ground_coverage",
            "front_setback", "rear_setback", "side_setback",
            "side_setback_left", "side_setback_right", "side_rear_margins",
            "maximum_height_m", "maximum_storeys",
            "car_parking_required", "two_wheeler_parking_required",
            "visitor_parking_required", "parking_area_required_m2",
            "fire_access_required", "fire_lift_required",
            "fire_staircase_required", "minimum_exit_count",
            "minimum_exit_width_m", "staircase_count", "staircase_width_m",
            "corridor_width_m", "lift_required", "lift_count",
            "accessible_entrance_required", "ramp_required", "ramp_width_m",
            "ramp_gradient", "minimum_open_space_m2",
            "recreational_open_space_m2", "amenity_space_m2",
            "road_widening", "reservation_present",
        ]

        # The production service must explicitly carry the selected
        # PostgreSQL evidence into the deterministic engine.  Without this
        # bridge MandatoryRuleEngine can only inspect structured RuleModel
        # rows, while the actual UDCPR values in this database are frequently
        # stored in canonical regulation/table source text.
        context_retriever = RegulatoryContextRetriever(
            collection=self.rule_resolver._chroma_collection,
            embedding_service=self.rule_resolver._embedding_service,
        )

        query = self._regulatory_query(facts, requested_fields)
        context = context_retriever.retrieve(
            query=query,
            requested_fields=requested_fields,
            top_k=100,
            related_regulation_limit=50,
            source_limit=10000,
        )

        # Candidate selection is closed-world. Never pass an empty selection
        # to MandatoryRuleEngine, because that would reopen the legacy path
        # that evaluates unrelated RuleModel rows.
        selected_regulations = [
            str(number).strip()
            for number in (context.metadata.get("selected_regulations") or [])
            if str(number).strip()
        ]

        constraints = PlanningConstraints()
        constraints.metadata.update({
            "regulatory_resolution_path": "chroma_openai_postgresql_deterministic",
            "selection_status": context.metadata.get(
                "selection_status",
                "SELECTED" if selected_regulations else "INSUFFICIENT_RULE_DATA",
            ),
            "selected_regulations": selected_regulations,
            "candidate_regulations": list(
                context.metadata.get("candidate_regulations") or []
            ),
        })

        if not selected_regulations or not context.sources:
            constraints.warnings.append(
                "Regulatory resolution stopped: no validated governing "
                "regulation with canonical PostgreSQL evidence was selected."
            )
            constraints.metadata.update({
                "mandatory_constraint_count": 0,
                "applicable_rule_ids": [],
                "unresolved_rule_ids": [],
                "not_applicable_rule_ids": [],
                "invalid_rule_ids": [],
                "regulatory_resolution_status": "insufficient_rule_data",
                "evaluation_passes": 0,
                "derived_regulatory_facts": self._derived_facts(
                    facts, constraints
                ),
            })
            return constraints

        engine = MandatoryRuleEngine()
        mandatory = engine.resolve(
            facts,
            selected_regulations=selected_regulations,
            regulatory_sources=list(context.sources),
            requested_fields=requested_fields,
        )

        # Only deterministic, verified MandatoryConstraints are promoted into
        # PlanningConstraints. Missing/unresolved values remain None.

        # PostgreSQL is authoritative. Promote resolved values into the
        # canonical PlanningFacts immediately; this does not calculate anything.
        for item in mandatory.constraints:
            if getattr(item, "value", None) is None:
                continue
            facts.set_resolved_value(
                str(item.key),
                item.value,
                rule_id=str(item.source_rule_id),
                regulation_id=str(item.regulation_id),
                unit=item.unit,
                source="postgresql_authoritative_table",
            )

        # Preserve genuine missing-input requests from the deterministic
        # PostgreSQL resolver. Never turn an empty result into "resolved".
        for warning in mandatory.warnings:
            prefix = "Authoritative source resolution: "
            if not str(warning).startswith(prefix):
                continue
            message = str(warning)[len(prefix):].strip()
            marker = "Missing PlanningFacts required to select applicable regulatory rows:"
            if marker in message:
                raw = message.split(marker, 1)[1]
                for field_name in raw.split(","):
                    field_name = field_name.strip()
                    if field_name:
                        facts.record_missing_input(
                            field_name,
                            reason="Required to select an applicable PostgreSQL regulatory table row.",
                        )
        for item in mandatory.constraints:
            key = str(item.key)
            if not hasattr(constraints, key):
                continue
            setattr(constraints, key, item.value)

            # Keep a compatible audit representation for callers that inspect
            # PlanningConstraints.applied_rules.  This record contains the
            # exact deterministic value; it is not a second regulatory engine.
            from townplanning.modules.planning.domain.applicable_rule import ApplicableRule
            constraints.applied_rules.append(
                ApplicableRule(
                    rule_id=str(item.source_rule_id),
                    regulation_id=str(item.regulation_id),
                    category=str(item.category),
                    name=str(item.rule_name),
                    description=str(item.reason),
                    priority=int(item.priority or 0),
                    status="applicable",
                    condition=dict(item.metadata.get("condition") or {}),
                    result={key: item.value},
                    reason=str(item.reason),
                    metadata={
                        **(item.metadata or {}),
                        "deterministic": True,
                        "source_rule_id": str(item.source_rule_id),
                    },
                )
            )

        # ``total_fsi`` is a derived planning value, not a regulatory value.
        # Keep the same non-circular definition used by the old service.
        if constraints.total_fsi is None:
            components = [
                constraints.basic_fsi,
                constraints.tdr_fsi,
                constraints.incentive_fsi,
            ]
            total_fsi = self._sum_numeric_components(components)
            if total_fsi is not None:
                constraints.total_fsi = total_fsi


        # Determine authoritative regulatory status FIRST.
        if facts.regulatory_errors:
            authoritative_status = "error"
        elif facts.regulatory_missing_inputs:
            authoritative_status = "needs_user_input"
        elif mandatory.constraints:
            authoritative_status = "resolved"
        else:
            authoritative_status = "insufficient_rule_data"

        constraints.metadata.update({
            "regulatory_resolution_path":
                "chroma_openai_postgresql_deterministic",
            "regulatory_resolution_status":
                authoritative_status,
            "selection_status":
                context.metadata.get("selection_status", "SELECTED"),
            "selected_regulations":
                selected_regulations,
            "mandatory_constraint_count":
                len(mandatory.constraints),
            "applicable_rule_ids":
                list(mandatory.applicable_rule_ids),
            "unresolved_rule_ids":
                list(mandatory.unresolved_rule_ids),
            "not_applicable_rule_ids":
                list(mandatory.not_applicable_rule_ids),
            "invalid_rule_ids":
                list(mandatory.invalid_rule_ids),
            "derived_regulatory_facts":
                self._derived_facts(facts, constraints),
            "evaluation_passes": 1,
        })



        return constraints

    def close(self):
        self.table_session.close()
