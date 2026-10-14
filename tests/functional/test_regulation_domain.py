from uuid import uuid4

from townplanning.modules.regulations.domain import (
    Regulation,
    KnowledgeCard,
    Rule,
)


def test_regulation_domain_workflow():

    regulation = Regulation(
        id=str(uuid4()),
        number="5.1.1",
        chapter="5",
        title="Development Permissible Adjacent to Gaothan",
        text="Development may be permitted...",
        page_start=85,
        page_end=86,
    )

    knowledge = KnowledgeCard(
        id=str(uuid4()),
        regulation_id=regulation.id,
        title=regulation.title,
        summary="Development adjacent to Gaothan is permitted.",
        purpose="Specify permissible development.",
        conditions=[
            "Within 500 m of Gaothan"
        ],
        measurements=[
            "500 m"
        ],
        keywords=[
            "Gaothan",
            "Regional Plan"
        ],
    )

    rule = Rule(
        id=str(uuid4()),
        regulation_id=regulation.id,
        category="distance",
        name="Maximum Distance",
        description="Development allowed within 500 m.",
        condition={
            "population": "<=5000"
        },
        result={
            "distance_m": 500
        },
    )

    assert knowledge.regulation_id == regulation.id
    assert rule.regulation_id == regulation.id
    assert rule.result["distance_m"] == 500
    assert knowledge.conditions[0] == "Within 500 m of Gaothan"