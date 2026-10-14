from __future__ import annotations

from typing import Any

from townplanning.infrastructure.database.models.rule_model import (
    RuleModel,
)

from townplanning.infrastructure.database.session import (
    SessionLocal,
)

from townplanning.modules.planning.domain.applicable_rule import (
    ApplicableRule,
)

from townplanning.modules.planning.rules.rule_condition_engine import (
    RuleConditionEngine,
)


class UDCPRRuleResolver:
    """
    Retrieves UDCPR rules from the database and evaluates
    their applicability against the current planning facts.

    The database is the authoritative source for UDCPR rules.

    This resolver does not use an LLM.

    Pipeline:

        Database Rules
              ↓
        RuleEvaluator
              ↓
        ApplicableRule
    """

    def __init__(
        self,
        session_factory=SessionLocal,
    ):

        self.session_factory = (
            session_factory
        )

        self.condition_engine = (
             RuleConditionEngine()
        )

    # --------------------------------------------------
    # Resolve rules
    # --------------------------------------------------

    def resolve(
        self,
        facts,
        categories: list[str] | None = None,
    ) -> list[ApplicableRule]:

        session = self.session_factory()
    
        try:
        
            query = (
                session.query(
                    RuleModel
                )
                .filter(
                    RuleModel.enabled.is_(True)
                )
            )
    
            if categories:
            
                query = query.filter(
                    RuleModel.category.in_(
                        categories
                    )
                )
    
            rules = (
                query
                .order_by(
                    RuleModel.priority.asc()
                )
                .all()
            )
    
            results: list[ApplicableRule] = []
    
            # Convert PlanningFacts once.
            if hasattr(facts, "to_dict"):
                fact_values = facts.to_dict()
            elif hasattr(facts, "__dict__"):
                fact_values = vars(facts)
            elif isinstance(facts, dict):
                fact_values = facts
            else:
                fact_values = facts
    
            for rule in rules:
            
                condition = (
                    rule.condition_json
                    or {}
                )
    
                result = (
                    rule.result_json
                    or {}
                )
    
                rule_metadata = (
                    dict(rule.metadata)
                    if isinstance(
                        rule.metadata,
                        dict,
                    )
                    else {}
                )
    
                try:
                
                    evaluation = (
                        self.condition_engine.evaluate(
                            condition,
                            fact_values,
                        )
                    )
    
                except Exception as exc:
                
                    results.append(
                        ApplicableRule(
                            rule_id=str(
                                rule.id
                            ),
                            regulation_id=str(
                                rule.regulation_id
                            ),
                            category=(
                                rule.category
                            ),
                            name=(
                                rule.name
                            ),
                            description=getattr(
                                rule,
                                "description",
                                "",
                            ) or "",
                            priority=(
                                rule.priority
                            ),
                            status="unresolved",
                            condition=dict(
                                condition
                            ),
                            result=dict(
                                result
                            ),
                            reason=(
                                "Condition "
                                "evaluation failed: "
                                f"{exc}"
                            ),
                            metadata=(
                                rule_metadata
                            ),
                        )
                    )
    
                    continue
                
                results.append(
                    ApplicableRule(
                        rule_id=str(
                            rule.id
                        ),
                        regulation_id=str(
                            rule.regulation_id
                        ),
                        category=(
                            rule.category
                        ),
                        name=(
                            rule.name
                        ),
                        description=getattr(
                            rule,
                            "description",
                            "",
                        ) or "",
                        priority=(
                            rule.priority
                        ),
                        status=(
                            evaluation.status
                        ),
                        condition=dict(
                            condition
                        ),
                        result=dict(
                            result
                        ),
                        reason=(
                            evaluation.reason
                        ),
                        metadata=(
                            rule_metadata
                        ),
                    )
                )
    
            return results
    
        finally:
        
            session.close()
        # --------------------------------------------------
        # Resolve important planning categories
        # --------------------------------------------------

    def resolve_building_rules(
        self,
        facts,
    ) -> list[ApplicableRule]:

        categories = [

            # FSI
            "FSI",
            "FSI Calculation",
            "FSI Computation",
            "FSI Regulations",
            "FSI Utilization",
            "Building FSI",

            # Height
            "Building Height",
            "Building Height & Lifts",
            "Height",
            "Height Regulation",
            "Height Restrictions",
            "Height Specification",

            # Setbacks
            "Setback",
            "Setbacks",
            "Building Setbacks",
            "Boundary & Setback",
            "Boundary Setbacks",
            "Setback Regulations",
            "Setback Regulation",

            # Building
            "Building",
            "Building Design",
            "Building Layout",
            "Building Requirements",
            "Building Standards",
            "Building Type",
            "Building Types",

            # Parking
            "Parking",

            # Roads
            "Road Width",
            "Roads",
            "Roads & Margins",

            # Fire
            "Fire Safety",

            # Circulation
            "Staircase",
            "Accessibility",
            "Egress",
            "Exit Requirements",

            # Light / ventilation
            "Light and Ventilation",

            # Coverage
            "Ground Coverage",

            # Open space
            "Open Space",
            "Open Space Requirement",
            "Open Spaces",
        ]

        return self.resolve(
            facts,
            categories=categories,
        )