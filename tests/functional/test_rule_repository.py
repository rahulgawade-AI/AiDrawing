from uuid import uuid4

from townplanning.modules.regulations.domain import Rule

from townplanning.infrastructure.database.repositories import (
    SQLAlchemyRuleRepository,
)

from townplanning.infrastructure.database.session import (
    SessionLocal,
)


def test_rule_repository():

    session = SessionLocal()

    repo = SQLAlchemyRuleRepository(
        session
    )

    rule = Rule(

        id=str(uuid4()),

        regulation_id=str(uuid4()),

        category="FSI",

        name="Maximum FSI",

        description="Maximum permissible FSI",

        condition={

            "zone": "Residential",

        },

        result={

            "fsi": 1.5,

        },

        priority=1,

        enabled=True,

        metadata={},
    )

    # -----------------------------------------

    repo.save(
        rule
    )

    loaded = repo.get(
        rule.id
    )

    assert loaded is not None

    assert loaded.id == rule.id

    assert loaded.name == "Maximum FSI"

    assert loaded.category == "FSI"

    assert loaded.condition["zone"] == "Residential"

    assert loaded.result["fsi"] == 1.5

    assert repo.exists(
        rule.id
    )

    # -----------------------------------------

    rules = repo.list()

    assert len(rules) > 0

    regulation_rules = repo.list_by_regulation(
        rule.regulation_id
    )

    assert len(regulation_rules) == 1

    assert regulation_rules[0].id == rule.id

    # -----------------------------------------

    repo.delete(
        rule.id
    )

    assert not repo.exists(
        rule.id
    )

    session.close()