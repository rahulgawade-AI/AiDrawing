"""
Converts between Domain and ORM Rule objects.
"""

from townplanning.infrastructure.database.models import RuleModel
from townplanning.modules.regulations.domain import Rule


class RuleMapper:

    @staticmethod
    def to_model(
        rule: Rule,
    ) -> RuleModel:

        return RuleModel(

            id=rule.id,

            regulation_id=rule.regulation_id,

            category=rule.category,

            name=rule.name,

            description=rule.description,

            condition_json=rule.condition,

            result_json=rule.result,

            priority=rule.priority,

            enabled=rule.enabled,

            metadata_json=rule.metadata,
        )

    @staticmethod
    def to_domain(
        model: RuleModel,
    ) -> Rule:

        return Rule(

            id=model.id,

            regulation_id=model.regulation_id,

            category=model.category,

            name=model.name,

            description=model.description,

            condition=model.condition_json,

            result=model.result_json,

            priority=model.priority,

            enabled=model.enabled,

            metadata=model.metadata_json,
        )