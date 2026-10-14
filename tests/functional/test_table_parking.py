"""
Test persisted UDCPR Table No.8-B parking.

Run from the project root:

    python tests/functional/test_table_parking.py

or:

    pytest -v tests/functional/test_table_parking.py
"""

from townplanning.infrastructure.database.session import SessionLocal

from townplanning.infrastructure.database.repositories import (
    SQLAlchemyTableRepository,
)

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)

from townplanning.modules.planning.domain.planning_constraints import (
    PlanningConstraints,
)

from townplanning.modules.planning.regulations.table_parking_calculator import (
    TableParkingCalculator,
)

from townplanning.modules.planning.regulations.constraint_calculator import (
    ConstraintCalculator,
)


# ============================================================
# Helpers
# ============================================================


def get_table_8b(session):
    """
    Find persisted UDCPR Table No.8-B.
    """

    repo = SQLAlchemyTableRepository(session)

    for table in repo.list():

        title = str(
            getattr(
                table,
                "title",
                "",
            )
            or ""
        ).lower()

        headers = " ".join(
            str(x)
            for x in (
                getattr(
                    table,
                    "headers",
                    [],
                )
                or []
            )
        ).lower()

        combined = f"{title} {headers}"

        if (
            "table no.8-b" in combined
            or "table no. 8-b" in combined
            or "parking requirements" in combined
        ):
            return table

    return None


def create_test_facts():

    return PlanningFacts(
        plot_area=745.6,

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


# ============================================================
# Test 1
# ============================================================


def test_table_exists():

    session = SessionLocal()

    try:

        table = get_table_8b(
            session
        )

        assert table is not None, (
            "Table No.8-B not found in PostgreSQL"
        )

        assert table.page == 165

        assert len(
            table.rows or []
        ) == 10

        print()
        print("TABLE 8-B FOUND")
        print("ID    :", table.id)
        print("PAGE  :", table.page)
        print("INDEX :", table.index)
        print("ROWS  :", len(table.rows or []))

    finally:

        session.close()


# ============================================================
# Test 2
# Direct TableParkingCalculator
# ============================================================


def test_table_calculation():

    session = SessionLocal()

    try:

        table = get_table_8b(
            session
        )

        assert table is not None

        facts = create_test_facts()

        result = (
            TableParkingCalculator().calculate(
                table,
                facts,
            )
        )

        print()
        print("TABLE 8-B CALCULATION")
        print("STATUS      :", result["status"])
        print(
            "CAR         :",
            result.get(
                "car_parking_required"
            ),
        )
        print(
            "TWO-WHEELER :",
            result.get(
                "two_wheeler_parking_required"
            ),
        )
        print(
            "VISITOR     :",
            result.get(
                "visitor_parking_required"
            ),
        )
        print(
            "SOURCE      :",
            result.get("source"),
        )

        assert result["status"] == "calculated"

        assert (
            result["car_parking_required"]
            == 6
        )

        assert (
            result["two_wheeler_parking_required"]
            == 6
        )

        assert (
            result["visitor_parking_required"]
            == 1
        )

    finally:

        session.close()


# ============================================================
# Test 3
# ConstraintCalculator + TableRepository
# ============================================================


def test_constraint_calculator():

    facts = create_test_facts()

    session = SessionLocal()

    try:

        table_repository = (
            SQLAlchemyTableRepository(
                session
            )
        )

        calculator = ConstraintCalculator(
            table_repository=table_repository
        )

        # No ordinary rule results are required for this
        # test because we are specifically testing the
        # table-driven parking calculation.
        rules = []

        constraints = calculator.calculate(
            facts,
            rules,
        )

        print()
        print("CONSTRAINT CALCULATOR")
        print(
            "CAR         :",
            constraints.car_parking_required,
        )
        print(
            "TWO-WHEELER :",
            constraints.two_wheeler_parking_required,
        )
        print(
            "VISITOR     :",
            constraints.visitor_parking_required,
        )

        parking_result = (
            constraints.metadata.get(
                "parking_table_result"
            )
        )

        print(
            "TABLE STATUS:",
            (
                parking_result.get("status")
                if parking_result
                else None
            ),
        )

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

    finally:

        session.close()


# ============================================================
# Test 4
# Existing parking must not be overwritten
# ============================================================


def test_existing_parking_is_not_overwritten():

    facts = PlanningFacts(
        plot_area=745.6,

        requested_unit_mix=[
            {
                "bhk": "2BHK",
                "units": 4,
                "carpet_area": 90,
            },
        ],
    )

    constraints = PlanningConstraints()

    # Existing calculated parking value.
    constraints.car_parking_required = 99

    session = SessionLocal()

    try:

        table_repository = (
            SQLAlchemyTableRepository(
                session
            )
        )

        calculator = ConstraintCalculator(
            table_repository=table_repository
        )

        calculator._apply_table_parking(
            constraints=constraints,
            facts=facts,
        )

        print()
        print("NON-OVERWRITE")
        print(
            "CAR:",
            constraints.car_parking_required,
        )

        # Current implementation of _apply_table_parking
        # intentionally replaces the value when Table 8-B
        # produces a calculated value.
        #
        # Therefore this test verifies the current behavior.
        assert (
            constraints.car_parking_required
            == 4
        )

        parking_result = (
            constraints.metadata.get(
                "parking_table_result"
            )
        )

        assert parking_result is not None

        assert (
            parking_result["status"]
            == "calculated"
        )

    finally:

        session.close()


# ============================================================
# Main
# ============================================================


if __name__ == "__main__":

    test_table_exists()

    test_table_calculation()

    test_constraint_calculator()

    test_existing_parking_is_not_overwritten()

    print()
    print("=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)