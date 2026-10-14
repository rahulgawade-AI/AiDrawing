from __future__ import annotations

import pytest

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.modules.regulations.extraction.postgresql_authoritative_table_resolver import (
    PostgreSQLAuthoritativeTableResolver,
)
from townplanning.modules.planning.domain import PlanningFacts


SELECTED_REGULATIONS = ["6.2.1", "6.3", "8.2.1", "8.2.2"]

PLANNING_FACT_CONSTRAINT_FIELDS = [
    "front_setback",
    "rear_setback",
    "side_setback_left",
    "side_setback_right",
    "basic_fsi",
    "premium_fsi",
    "tdr_fsi",
    "maximum_fsi",
    "car_parking_required",
    "two_wheeler_parking_required",
    "visitor_parking_required",
    "parking_factor",
]

EXPECTED_TABLES = {
    "front_setback": "6-D",
    "rear_setback": "6-D",
    "side_setback_left": "6-D",
    "side_setback_right": "6-D",
    "basic_fsi": "6-G",
    "premium_fsi": "6-G",
    "tdr_fsi": "6-G",
    "maximum_fsi": "6-G",
    "car_parking_required": "8-B",
    "two_wheeler_parking_required": "8-B",
    "visitor_parking_required": "8-B",
    "parking_factor": "8-C",
}


def build_test_facts():
    facts = PlanningFacts()
    facts.road_width = 12.0
    authority = "Pune Municipal Corporation"
    facts.planning_authority = authority
    facts.municipality = authority
    facts.municipal_corporation = authority
    facts.competent_authority = authority
    facts.occupancy = "residential"
    facts.tenement_carpet_areas = [69.67728000000001, 69.67728000000001]
    facts.plot_area = None
    facts.building_height = None
    return facts


def build_sources():
    return [
        {
            "regulation_number": "6.2.1",
            "source_type": "paragraph",
            "source_text": (
                "6.2.1 Marginal distances shall be as per Table 6-D for residential "
                "buildings and mixed uses."
            ),
        },
        {
            "regulation_number": "6.2.3",
            "source_type": "paragraph",
            "source_text": (
                "6.2.3 The front margin shall be as per Table 6-D irrespective of "
                "height; side and rear margins shall be as specified in Table 6-D "
                "and Table 6-E where applicable."
            ),
        },
        {
            "regulation_number": "6.3",
            "source_type": "paragraph",
            "source_text": "6.3 PERMISSIBLE FSI. The permissible FSI is given in Table 6-G.",
        },
        {
            "regulation_number": "8.2.1",
            "source_type": "paragraph",
            "source_text": (
                "8.2.1 Parking spaces required shall be as per Table 8-B. "
                "The factors in Table 8-C of Regulation 8.2.2 shall also apply."
            ),
        },
        {
            "regulation_number": "8.2.2",
            "source_type": "paragraph",
            "source_text": "8.2.2 The multiplying factors for parking are given in Table 8-C.",
        },
    ]


def _constraint_map(result):
    return {
        getattr(c, "key", None): c
        for c in (getattr(result, "constraints", []) or [])
        if getattr(c, "key", None)
    }


@pytest.fixture
def resolver():
    session = SessionLocal()
    try:
        yield PostgreSQLAuthoritativeTableResolver(session)
    finally:
        session.close()


def test_all_requested_constraints_are_resolved_from_selected_evidence(resolver):
    result = resolver.resolve(
        facts=build_test_facts(),
        selected_regulations=SELECTED_REGULATIONS,
        chroma_sources=build_sources(),
        requested_fields=PLANNING_FACT_CONSTRAINT_FIELDS,
    )
    constraints = _constraint_map(result)
    missing = [f for f in PLANNING_FACT_CONSTRAINT_FIELDS if f not in constraints]
    assert not missing, (
        "Requested PlanningFacts constraints were not returned:\n"
        f"{missing}\n\nReturned keys: {sorted(constraints)}\n\n"
        f"Warnings: {getattr(result, 'warnings', [])}"
    )


def test_resolved_constraints_have_correct_selected_source_provenance(resolver):
    result = resolver.resolve(
        facts=build_test_facts(),
        selected_regulations=SELECTED_REGULATIONS,
        chroma_sources=build_sources(),
        requested_fields=PLANNING_FACT_CONSTRAINT_FIELDS,
    )
    constraints = _constraint_map(result)
    assert set(constraints) == set(PLANNING_FACT_CONSTRAINT_FIELDS)
    for field, expected_table in EXPECTED_TABLES.items():
        c = constraints[field]
        metadata = getattr(c, "metadata", {}) or {}
        assert metadata.get("regulation_number") in SELECTED_REGULATIONS
        assert metadata.get("extraction") == "openai_selected_evidence"
        assert metadata.get("table_number") == expected_table
        assert metadata.get("source_type") == "table"


def test_selected_table_numbers_are_present(resolver):
    result = resolver.resolve(
        facts=build_test_facts(),
        selected_regulations=SELECTED_REGULATIONS,
        chroma_sources=build_sources(),
        requested_fields=PLANNING_FACT_CONSTRAINT_FIELDS,
    )
    selected = {
        (s.regulation_number, s.table_number.upper())
        for s in result.selections
    }
    for reg, table in [
        ("6.2.1", "6-D"),
        ("6.3", "6-G"),
        ("8.2.1", "8-B"),
        ("8.2.1", "8-C"),
        ("8.2.2", "8-C"),
    ]:
        assert (reg, table) in selected


def test_no_unselected_table_is_used_for_requested_constraints(resolver):
    result = resolver.resolve(
        facts=build_test_facts(),
        selected_regulations=SELECTED_REGULATIONS,
        chroma_sources=build_sources(),
        requested_fields=PLANNING_FACT_CONSTRAINT_FIELDS,
    )
    constraints = _constraint_map(result)
    for field, expected_table in EXPECTED_TABLES.items():
        metadata = constraints[field].metadata
        assert metadata.get("table_number") == expected_table
        assert metadata.get("regulation_number") in SELECTED_REGULATIONS


def test_chroma_complete_table_payload_is_used_when_available(resolver):
    sources = [{
        "regulation_number": "6.3",
        "table_number": "6-G",
        "source_type": "table",
        "source_text": "Regulation 6.3 identifies Table 6-G for permissible FSI.",
        "table_data": {
            "table_number": "6-G",
            "title": "Table 6-G",
            "headers": [
                "Road width in meters",
                "Basic FSI",
                "FSI on payment of premium",
                "Maximum permissible TDR loading",
                "Maximum building potential on plot including in-situ FSI",
            ],
            "rows": [
                ["9.0 m. and above but below 12.0 m.", "1.10", "0.50", "0.40", "2.00"],
                ["12.0 m. and above but below 15.0 m.", "1.10", "0.50", "0.65", "2.25"],
            ],
            "markdown": "Table 6-G",
        },
    }]
    result = resolver.resolve(
        facts=build_test_facts(),
        selected_regulations=["6.3"],
        chroma_sources=sources,
        requested_fields=["basic_fsi", "premium_fsi", "tdr_fsi", "maximum_fsi"],
    )
    constraints = _constraint_map(result)
    assert {"basic_fsi", "premium_fsi", "tdr_fsi", "maximum_fsi"}.issubset(constraints)
    for field in ["basic_fsi", "premium_fsi", "tdr_fsi", "maximum_fsi"]:
        assert constraints[field].metadata.get("table_number") == "6-G"
        assert constraints[field].metadata.get("source") == "chroma"
def test_missing_road_width_is_reported_for_setback_constraints(resolver):
    facts = build_test_facts()
    facts.road_width = None

    result = resolver.resolve(
        facts=facts,
        selected_regulations=["6.2.1"],
        chroma_sources=build_sources(),
        requested_fields=[
            "front_setback",
            "rear_setback",
            "side_setback_left",
            "side_setback_right",
        ],
    )

    constraints = _constraint_map(result)

    # Setback constraints must not be fabricated without road width.
    assert not any(
        field in constraints
        for field in [
            "front_setback",
            "rear_setback",
            "side_setback_left",
            "side_setback_right",
        ]
    )

    assert "road_width" in result.missing_inputs

    assert any(
        "front_setback" in warning and "road_width" in warning
        for warning in result.warnings
    )


def test_missing_tenement_carpet_areas_is_reported_for_parking_constraints(
    resolver,
):
    facts = build_test_facts()
    facts.tenement_carpet_areas = None

    result = resolver.resolve(
        facts=facts,
        selected_regulations=["8.2.1"],
        chroma_sources=build_sources(),
        requested_fields=[
            "car_parking_required",
            "two_wheeler_parking_required",
            "visitor_parking_required",
        ],
    )

    constraints = _constraint_map(result)

    # Parking requirements must not be fabricated without
    # the tenement carpet-area input.
    assert not any(
        field in constraints
        for field in [
            "car_parking_required",
            "two_wheeler_parking_required",
            "visitor_parking_required",
        ]
    )

    assert "tenement_carpet_areas" in result.missing_inputs

    assert any(
        "car_parking_required" in warning
        and "tenement_carpet_areas" in warning
        for warning in result.warnings
    )


def test_missing_planning_authority_is_reported_for_parking_factor(resolver):
    facts = build_test_facts()

    facts.planning_authority = None
    facts.municipality = None
    facts.municipal_corporation = None
    facts.competent_authority = None

    result = resolver.resolve(
        facts=facts,
        selected_regulations=["8.2.2"],
        chroma_sources=build_sources(),
        requested_fields=["parking_factor"],
    )

    constraints = _constraint_map(result)

    # Parking factor must not be fabricated without the
    # authority input used to select the applicable factor.
    assert "parking_factor" not in constraints

    assert "planning_authority" in result.missing_inputs

    assert any(
        "parking_factor" in warning and "planning_authority" in warning
        for warning in result.warnings
    )


def test_missing_inputs_make_result_insufficient_rule_data(resolver):
    facts = build_test_facts()
    facts.road_width = None

    result = resolver.resolve(
        facts=facts,
        selected_regulations=["6.2.1"],
        chroma_sources=build_sources(),
        requested_fields=[
            "front_setback",
            "rear_setback",
            "side_setback_left",
            "side_setback_right",
        ],
    )

    assert "road_width" in result.missing_inputs
    assert result.status == "INSUFFICIENT_RULE_DATA"


def test_resolver_only_extracts_fields_with_required_inputs(monkeypatch):
    resolver = PostgreSQLAuthoritativeTableResolver(session=None)
    def build_mock_evidence(**kwargs):
        kwargs["result"].selections.append(
            type(
                "Selection",
                (),
                {
                    "regulation_number": "6.2.1",
                    "table_number": "6-D",
                    "table_title": "Table 6-D",
                    "table": None,
                    "reason": "test evidence",
                    "source_text": "mock evidence",
                    "source_kind": "postgresql",
                },
            )()
        )

    monkeypatch.setattr(resolver, "_build_selected_evidence", build_mock_evidence)
    calls = []

    def extract_selected(**kwargs):
        calls.append(kwargs)
        resolver._last_openai_missing_fields = list(kwargs["requested_fields"])
        return []

    monkeypatch.setattr(
        resolver, "_extract_selected_evidence_with_openai", extract_selected
    )

    facts = PlanningFacts()
    facts.road_width = None
    result = resolver.resolve(
        facts=facts,
        selected_regulations=["6.2.1"],
        chroma_sources=[],
        requested_fields=["front_setback", "maximum_height_m"],
    )

    assert len(calls) == 1
    assert calls[0]["requested_fields"] == ["maximum_height_m"]
    assert "road_width" in result.missing_inputs
