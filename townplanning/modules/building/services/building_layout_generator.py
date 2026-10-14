from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from townplanning.modules.building.domain.building_design_plan import (
    BuildingDesignPlan,
)
from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)


@dataclass(slots=True)
class BuildingLayoutResult:
    """
    Preliminary building-layout envelope.

    This is NOT an architectural model.

    It contains only geometry that can be derived safely from
    the available PlanningFacts and BuildingDesignPlan.

    No regulatory values are invented here.
    """

    feasible: bool

    reason: str | None = None

    plot_area_m2: float | None = None

    maximum_built_up_area_m2: float | None = None

    maximum_ground_coverage_m2: float | None = None

    buildable_area_m2: float | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:

        result = {
            "feasible": self.feasible,
            "reason": self.reason,
            "plot_area_m2": self.plot_area_m2,
            "maximum_built_up_area_m2":
                self.maximum_built_up_area_m2,
            "maximum_ground_coverage_m2":
                self.maximum_ground_coverage_m2,
            "buildable_area_m2":
                self.buildable_area_m2,
            "metadata": dict(self.metadata),
        }

        return {
            key: value
            for key, value in result.items()
            if value is not None
        }


class BuildingLayoutGenerator:
    """
    Converts the deterministic BuildingDesignPlan into a
    preliminary layout envelope.

    IMPORTANT:

    This class does not:

        - invent setbacks
        - invent ground coverage
        - invent building height
        - invent number of floors
        - invent room dimensions
        - create architectural objects
        - create walls
        - create doors
        - create windows
        - create columns
        - create beams
        - create stairs
        - create parking layouts

    Those operations require additional resolved inputs and
    domain models.
    """

    def generate(
        self,
        facts: PlanningFacts,
        plan: BuildingDesignPlan,
    ) -> BuildingLayoutResult:

        if facts is None:
            raise ValueError(
                "PlanningFacts are required."
            )

        if plan is None:
            raise ValueError(
                "BuildingDesignPlan is required."
            )

        # --------------------------------------------------
        # Plot area
        # --------------------------------------------------

        plot_area = plan.plot_area_m2

        if plot_area is None:
            return BuildingLayoutResult(
                feasible=False,
                reason=(
                    "Plot area is required before "
                    "building layout generation."
                ),
            )

        # --------------------------------------------------
        # Maximum built-up area
        # --------------------------------------------------

        maximum_built_up_area = (
            plan.maximum_built_up_area_m2
        )

        # --------------------------------------------------
        # Ground coverage
        #
        # Do NOT derive this from FSI.
        #
        # Ground coverage is a separate planning
        # constraint.
        # --------------------------------------------------

        ground_coverage = (
            plan.maximum_ground_coverage_m2
        )

        # --------------------------------------------------
        # Current implementation can only produce a
        # conceptual envelope when ground coverage is known.
        #
        # Without it, generating a footprint would require
        # inventing a regulatory value.
        # --------------------------------------------------

        if ground_coverage is None:

            return BuildingLayoutResult(
                feasible=False,

                reason=(
                    "Maximum ground coverage is not "
                    "resolved. A building footprint cannot "
                    "be generated without inventing a "
                    "regulatory value."
                ),

                plot_area_m2=plot_area,

                maximum_built_up_area_m2=(
                    maximum_built_up_area
                ),

                maximum_ground_coverage_m2=None,

                metadata={
                    "status": "CONSTRAINTS_INCOMPLETE",

                    "required_for_footprint": [
                        "maximum_ground_coverage_m2",
                    ],

                    "maximum_fsi": (
                        plan.maximum_fsi
                    ),

                    "front_setback_m": (
                        plan.front_setback_m
                    ),

                    "rear_setback_m": (
                        plan.rear_setback_m
                    ),

                    "side_setback_left_m": (
                        plan.side_setback_left_m
                    ),

                    "side_setback_right_m": (
                        plan.side_setback_right_m
                    ),
                },
            )

        # --------------------------------------------------
        # Ground coverage cannot exceed plot area.
        #
        # This is a geometric consistency check, not a
        # regulatory calculation.
        # --------------------------------------------------

        if ground_coverage > plot_area:

            return BuildingLayoutResult(
                feasible=False,

                reason=(
                    "Maximum ground coverage exceeds "
                    "the plot area."
                ),

                plot_area_m2=plot_area,

                maximum_built_up_area_m2=(
                    maximum_built_up_area
                ),

                maximum_ground_coverage_m2=(
                    ground_coverage
                ),

                metadata={
                    "status": "INVALID_CONSTRAINT_SET",
                },
            )

        # --------------------------------------------------
        # A resolved ground coverage gives us the maximum
        # footprint envelope.
        # --------------------------------------------------

        return BuildingLayoutResult(
            feasible=True,

            plot_area_m2=plot_area,

            maximum_built_up_area_m2=(
                maximum_built_up_area
            ),

            maximum_ground_coverage_m2=(
                ground_coverage
            ),

            buildable_area_m2=(
                ground_coverage
            ),

            metadata={
                "status": "FOOTPRINT_ENVELOPE_AVAILABLE",

                "maximum_fsi": (
                    plan.maximum_fsi
                ),

                "front_setback_m": (
                    plan.front_setback_m
                ),

                "rear_setback_m": (
                    plan.rear_setback_m
                ),

                "side_setback_left_m": (
                    plan.side_setback_left_m
                ),

                "side_setback_right_m": (
                    plan.side_setback_right_m
                ),

                "maximum_height_m": (
                    plan.maximum_height_m
                ),

                "maximum_storeys": (
                    plan.maximum_storeys
                ),
            },
        )
