"""
End-to-end PlanningService test.

Verifies:

    PlanningFacts
        ↓
    PlanningService
        ↓
    UDCPRRuleResolver
        ↓
    ConstraintCalculator
        ↓
    SQLAlchemyTableRepository
        ↓
    PostgreSQL Table No.8-B
        ↓
    TableParkingCalculator
        ↓
    PlanningConstraints
"""

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.services.planning_service import (
    PlanningService,
)


def test_planning_service_table_8b():

    facts = PlanningFacts(
        plot_area=745.6,

        road_width=12.0,

        building_type="residential",

        building_use="residential",

        requested_unit_mix=[
            {
                "bhk": "2BHK",
                "units": 4,
                "carpet_area": 90,
            },
            {
                "bhk": "3BHK",
                "units": 2,
                "carpet_area": 125,
            },
        ],
    )

    service = PlanningService()

    try:

        constraints = service.evaluate(
            facts
        )

        print()
        print("=" * 80)
        print("PLANNING SERVICE - TABLE 8-B")
        print("=" * 80)

        print(
            "CAR PARKING         :",
            constraints.car_parking_required,
        )

        print(
            "TWO-WHEELER PARKING :",
            constraints.two_wheeler_parking_required,
        )

        print(
            "VISITOR PARKING     :",
            constraints.visitor_parking_required,
        )

        parking_result = (
            constraints.metadata.get(
                "parking_table_result"
            )
        )

        print(
            "TABLE STATUS        :",
            (
                parking_result.get("status")
                if parking_result
                else None
            ),
        )

        print(
            "TABLE               :",
            (
                parking_result.get("source")
                if parking_result
                else None
            ),
        )

        print(
            "EVALUATION PASSES   :",
            constraints.metadata.get(
                "evaluation_passes"
            ),
        )

        print(
            "DERIVED FACTS       :",
            constraints.metadata.get(
                "derived_regulatory_facts"
            ),
        )

        print("=" * 80)

        # --------------------------------------------------
        # Table 8-B must have participated in the real
        # PlanningService calculation.
        # --------------------------------------------------

        assert parking_result is not None

        assert (
            parking_result["status"]
            == "calculated"
        )

        assert (
            constraints.car_parking_required
            == 6
        )

        assert (
            constraints.two_wheeler_parking_required
            == 6
        )

        assert (
            constraints.visitor_parking_required
            == 1
        )

        assert (
            constraints.metadata[
                "evaluation_passes"
            ]
            == 2
        )

    finally:

        # PlanningService currently owns the table DB session.
        if hasattr(
            service,
            "table_session",
        ):
            service.table_session.close()


if __name__ == "__main__":

    test_planning_service_table_8b()

    print()
    print("=" * 80)
    print("PLANNING SERVICE TEST PASSED")
    print("=" * 80)
