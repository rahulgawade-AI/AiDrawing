from __future__ import annotations

import json
from typing import Any

from townplanning.core.container import ApplicationContainer

from townplanning.infrastructure.database.session import SessionLocal
from townplanning.infrastructure.database.repositories import (
    SQLAlchemyTableRepository,
)

from townplanning.modules.planning.fact_context import (
    PlanningFactContext,
)

from townplanning.modules.planning.services.planning_service import (
    PlanningService,
)

from townplanning.modules.planning.llm.constraint_discovery import (
    ConstraintDiscoveryService,
)


#MODEL = "gemma3:12b"
MODEL = "gpt-5.6-terra"


def print_value(name: str, value: Any) -> None:
    print(f"{name:<40} = {value}")


def print_project_context(
    context: PlanningFactContext,
) -> None:

    print()
    print("=" * 100)
    print("PROJECT CONTEXT")
    print("=" * 100)

    values = context.to_dict()

    values.update(
        {
            "project_classification":
                "Residential apartment / group housing",

            "occupancy_classification":
                "Multi-family residential",

            "ordinary_residential_project":
                True,

            "special_planning_authority_project":
                False,

            "affordable_housing_project":
                bool(
                    getattr(
                        context,
                        "affordable_housing",
                        False,
                    )
                ),

            "hotel":
                bool(
                    getattr(
                        context,
                        "hotel",
                        False,
                    )
                ),

            "hospital":
                bool(
                    getattr(
                        context,
                        "hospital",
                        False,
                    )
                ),

            "restaurant":
                bool(
                    getattr(
                        context,
                        "restaurant",
                        False,
                    )
                ),

            "school":
                bool(
                    getattr(
                        context,
                        "school",
                        False,
                    )
                ),
        }
    )

    for key, value in values.items():
        print_value(
            key,
            value,
        )


def print_rules_summary(
    rules: list[Any],
) -> None:

    print()
    print("=" * 100)
    print("DETERMINISTIC RULES")
    print("=" * 100)

    print(
        "TOTAL RULES:",
        len(rules),
    )

    applicable = sum(
        1
        for rule in rules
        if rule.is_applicable
    )

    unresolved = sum(
        1
        for rule in rules
        if rule.is_unresolved
    )

    print(
        "APPLICABLE:",
        applicable,
    )

    print(
        "UNRESOLVED:",
        unresolved,
    )

def print_constraint(
    constraint: dict[str, Any],
) -> None:

    print()
    print("-" * 100)

    print(
        "ID            :",
        constraint.get(
            "constraint_id",
            constraint.get(
                "id"
            ),
        ),
    )

    print(
        "NAME          :",
        constraint.get(
            "name"
        ),
    )

    print(
        "CATEGORY      :",
        constraint.get(
            "category"
        ),
    )

    print(
        "APPLICABILITY :",
        constraint.get(
            "applicability"
        ),
    )

    print(
        "STATUS        :",
        constraint.get(
            "status"
        ),
    )

    print(
        "VALUE         :",
        constraint.get(
            "value"
        ),
    )

    print(
        "UNIT          :",
        constraint.get(
            "unit"
        ),
    )

    print(
        "OPERATOR      :",
        constraint.get(
            "operator"
        ),
    )

    print(
        "REQUIRED INPUTS:",
        constraint.get(
            "required_inputs",
            [],
        ),
    )

    print(
        "RATIONALE     :",
        constraint.get(
            "rationale",
            constraint.get(
                "reason"
            ),
        ),
    )

    print(
        "SOURCE RULES  :",
        constraint.get(
            "source_rule_ids",
            constraint.get(
                "source_rules",
                [],
            ),
        ),
    )

    # print_chroma_testrint(
    #     "SOURCE TABLES :",
    #     constraint.get(
    #         "source_tables",
    #         [],
    #     ),
    # )

    print(
        "SOURCE PDF    :",
        constraint.get(
            "source_pdf_pages",
            constraint.get(
                "source_pages",
                [],
            ),
        ),
    )

    print(
        "REGULATIONS   :",
        constraint.get(
            "regulation_references",
            [],
        ),
    )

    print(
        "DEPENDENCIES  :",
        constraint.get(
            "dependencies",
            [],
        ),
    )

    print(
        "CALCULATION   :",
        constraint.get(
            "calculation"
        ),
    )


def main() -> None:

    # ==================================================================
    # PROJECT INPUT
    # ==================================================================

    context = PlanningFactContext(
        project_id="TEST-RES-001",

        project_type=(
            "Residential Apartment"
        ),

        development_type=(
            "New Construction"
        ),

        # --------------------------------------------------------------
        # SITE
        # --------------------------------------------------------------

        plot_area=745.6,

        plot_number="78/5",

        north_direction=0.0,

        plot_shape="irregular",

        # --------------------------------------------------------------
        # ROAD / ACCESS
        # --------------------------------------------------------------

        road_width=18.0,

        road_widths=[
            18.0
        ],

        road_frontage_count=1,

        road_locations=[
            "south"
        ],

        road_type="Urban road",

        access_available=True,

        # --------------------------------------------------------------
        # LOCATION
        # --------------------------------------------------------------

        location="Hadapsar, Pune, Maharashtra, India",

        city="Pune",

        district="Pune",

        state="Maharashtra",

        # --------------------------------------------------------------
        # PLANNING AUTHORITY
        # --------------------------------------------------------------

        planning_authority=(
            "Pune Municipal Corporation"
        ),

        municipality=(
            "Pune Municipal Corporation"
        ),

        # --------------------------------------------------------------
        # ZONING
        # --------------------------------------------------------------

        zone_type="Residential",

        land_use_zone="Residential",

        land_use_classification=(
            "Residential"
        ),

        congested_area=False,

        tod_zone=False,

        heritage_zone=False,

        crz_zone=False,

        eco_sensitive_zone=False,

        airport_restriction=False,

        reservation_present=False,

        # --------------------------------------------------------------
        # BUILDING
        # --------------------------------------------------------------

        building_type=(
            "Residential Apartment"
        ),

        building_use="residential",

        mixed_use=False,

        group_housing=True,

        redevelopment=False,

        rehabilitation=False,

        existing_building=False,

        floor_height=3.0,

        # --------------------------------------------------------------
        # USER REQUIREMENTS
        # --------------------------------------------------------------

        requested_units=6,

        requested_1bhk_units=0,

        requested_2bhk_units=4,

        requested_3bhk_units=2,

        requested_unit_mix=[
            {
                "bhk": "2BHK",
                "units": 4,
                "carpet_area": 90.0,
            },
            {
                "bhk": "3BHK",
                "units": 2,
                "carpet_area": 125.0,
            },
        ],

        requested_commercial_area=0.0,

        requested_residential_area=(
            4 * 90.0
            +
            2 * 125.0
        ),

        maximize_fsi=True,

        maximize_parking=True,

        maximize_usable_area=True,

        optimize_daylight=True,

        optimize_ventilation=True,

        # --------------------------------------------------------------
        # ADDITIONAL PROJECT CLASSIFICATION FACTS
        # --------------------------------------------------------------

        additional_facts={

            "ownership_type": None,

            "affordable_housing": False,

            "mhada_project": False,

            "pap_project": False,

            "staff_quarters": False,

            "hotel": False,

            "hospital": False,

            "restaurant": False,

            "school": False,

            "educational_institution": False,

            "commercial_project": False,

            "industrial_project": False,

            "religious_building": False,

            "assembly_building": False,

            "institutional_building": False,

            "parking_requirement_override": None,

            "existing_fsi": None,

            "tdr_proposed": None,

            "premium_fsi_proposed": None,

            "plot_image_available": False,

            "boundary_detected": False,

            "road_detected": True,

            "north_detected": False,

            "existing_structures_detected": False,

            "project_classification": (
                "Residential apartment / group housing"
            ),

            "occupancy_classification": (
                "Multi-family residential"
            ),

            "ordinary_residential_project": True,

            "special_planning_authority_project": False,

            "affordable_housing_project": False,

            "rehabilitation_project": False,

            "redevelopment_project": False,

            "mixed_use_project": False,
             "locality": "Hadapsar",
    "jurisdiction": "Pune Municipal Corporation",
        },
    )

    # ==================================================================
    # DISPLAY PROJECT
    # ==================================================================

    print_project_context(
        context
    )

    # ==================================================================
    # CANONICAL PLANNING FACTS
    # ==================================================================

    facts = (
        context.to_planning_facts()
    )

    # ==================================================================
    # EXISTING PLANNING SERVICE
    # ==================================================================

    planning_service = (
        PlanningService()
    )

    rules = (
        planning_service
        .rule_resolver
        .resolve_building_rules(
            facts
        )
    )

    print()
    print("=" * 100)
    print("APPLICABLE RULE IDs - EXACT PRODUCTION RESOLVER")
    print("=" * 100)

    applicable_ids = []

    for rule in rules:

        if getattr(
            rule,
            "status",
            "",
        ) == "applicable":

            applicable_ids.append(
                str(
                    getattr(
                        rule,
                        "rule_id",
                        "",
                    )
                )
            )

    print(
        "APPLICABLE RULE COUNT:",
        len(applicable_ids),
    )

    for rule_id in applicable_ids:
        print(
            rule_id
        )

        print_rules_summary(
            rules
        )

    # ==================================================================
    # EXISTING APPLICATION CONTAINER
    #
    # This uses:
    #
    #   Ollama embedding provider
    #          ↓
    #   EmbeddingService
    #          ↓
    #   ChromaRepository
    #          ↓
    #   SemanticSearchService
    #
    # and therefore the existing:
    #
    #   ./data/chroma
    #   collection = townplanning
    #
    # ==================================================================

    container = (
        ApplicationContainer()
    )

    semantic_search = (
        container
        .semantic_search_service()
    )

    # ==================================================================
    # TEST CHROMA FIRST
    # ==================================================================

    # print_chroma_test(
    #     semantic_search
    # )

    # ==================================================================
    # POSTGRES TABLE REPOSITORY
    # ==================================================================

    session = SessionLocal()

    try:

        table_repository = (
            SQLAlchemyTableRepository(
                session
            )
        )

        # ==============================================================
        # CONSTRAINT DISCOVERY
        # ==============================================================

        discovery = (
            ConstraintDiscoveryService(

                table_repository=(
                    table_repository
                ),

                rule_resolver=(
                    planning_service
                    .rule_resolver
                ),

                vector_search_service=(
                    semantic_search
                ),

                model=MODEL,
            )
        )

        # ==============================================================
        # CONFIGURATION
        # ==============================================================

        print()
        print("=" * 100)
        print("OLLAMA CONFIGURATION")
        print("=" * 100)

        print(
            "MODEL:",
            discovery.model,
        )

        print(
            "OLLAMA:",
            getattr(
                discovery.ollama,
                "base_url",
                "unknown",
            ),
        )

        print(
            "TIMEOUT:",
            getattr(
                discovery.ollama,
                "timeout",
                "unknown",
            ),
        )

        # ==============================================================
        # DISCOVERY
        # ==============================================================

        result = (
            discovery.discover(
                facts,
                rules=rules,
            )
        )

    finally:

        session.close()

    # ==================================================================
    # RESULT
    # ==================================================================

    print()
    print("=" * 100)
    print("OLLAMA CONSTRAINT DISCOVERY")
    print("=" * 100)

    print(
        "STATUS :",
        result.status,
    )

    print(
        "MODEL  :",
        result.model,
    )

    print(
        "CONSTRAINT COUNT :",
        len(
            result.constraints
        ),
    )

    # ==================================================================
    # RAW GEMMA RESPONSE
    # ==================================================================

    print()
    print("=" * 100)
    print("RAW RESPONSE FROM GEMMA")
    print("=" * 100)

    print(
        result.raw_response
    )

    # ==================================================================
    # DISCOVERED CONSTRAINTS
    # ==================================================================

    print()
    print("=" * 100)
    print("DISCOVERED CONSTRAINTS")
    print("=" * 100)

    for constraint in (
        result.constraints
    ):

        if not isinstance(
            constraint,
            dict,
        ):
            print(
                constraint
            )
            continue

        print_constraint(
            constraint
        )

    # ==================================================================
    # EXCLUDED
    # ==================================================================

    print()
    print("=" * 100)
    print("EXCLUDED CONSTRAINTS")
    print("=" * 100)

    if not result.excluded_constraints:

        print(
            "None"
        )

    else:

        for item in (
            result.excluded_constraints
        ):

            print(
                json.dumps(
                    item,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            )

    # ==================================================================
    # UNRESOLVED
    # ==================================================================

    print()
    print("=" * 100)
    print("UNRESOLVED / NEEDS INFORMATION")
    print("=" * 100)

    if not result.unresolved:

        print(
            "None"
        )

    else:

        for item in result.unresolved:

            print(
                json.dumps(
                    item,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            )

    # ==================================================================
    # MISSING INFORMATION
    # ==================================================================

    print()
    print("=" * 100)
    print("MISSING INFORMATION")
    print("=" * 100)

    if not result.missing_information:

        print(
            "None"
        )

    else:

        for item in (
            result.missing_information
        ):

            print(
                json.dumps(
                    item,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            )

    # ==================================================================
    # RETRIEVAL DEBUG
    # ==================================================================

    print()
    print("=" * 100)
    print("RETRIEVAL DEBUG")
    print("=" * 100)

    print(
        json.dumps(
            result.retrieval,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    # ==================================================================
    # ERROR / REASON
    # ==================================================================

    if result.reason:

        print()
        print("=" * 100)
        print("ERROR / REASON")
        print("=" * 100)

        print(
            result.reason
        )


if __name__ == "__main__":
    main()