
from __future__ import annotations

from townplanning.modules.building.domain.building_design_plan import (
    BuildingDesignPlan,
)
from townplanning.modules.planning.domain.planning_constraints import (
    PlanningConstraints,
)
from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)


class BuildingDesignGenerator:
    """
    Converts deterministic PlanningFacts and PlanningConstraints
    into the canonical BuildingDesignPlan.

    This class does not calculate regulations.

    It only transfers already-resolved deterministic planning
    constraints into the building-design envelope.
    """

    def generate(
        self,
        facts: PlanningFacts,
        constraints: PlanningConstraints,
    ) -> BuildingDesignPlan:

        if facts is None:
            raise ValueError(
                "PlanningFacts are required."
            )

        if constraints is None:
            raise ValueError(
                "PlanningConstraints are required."
            )

        return BuildingDesignPlan(

            # --------------------------------------------------
            # SITE
            # --------------------------------------------------

            plot_area_m2=facts.plot_area,

            # --------------------------------------------------
            # FSI
            # --------------------------------------------------

            maximum_fsi=constraints.maximum_fsi,

            maximum_built_up_area_m2=(
                constraints.maximum_built_up_area
            ),

            # --------------------------------------------------
            # SITE COVERAGE / SETBACKS
            # --------------------------------------------------

            maximum_ground_coverage_m2=(
                constraints.maximum_ground_coverage
            ),

            front_setback_m=(
                constraints.front_setback
            ),

            rear_setback_m=(
                constraints.rear_setback
            ),

            side_setback_left_m=(
                constraints.side_setback_left
            ),

            side_setback_right_m=(
                constraints.side_setback_right
            ),

            minimum_open_space_m2=(
                constraints.minimum_open_space
            ),

            # --------------------------------------------------
            # HEIGHT
            # --------------------------------------------------

            maximum_height_m=(
                constraints.maximum_height_m
            ),

            maximum_storeys=(
                constraints.maximum_storeys
            ),

            # --------------------------------------------------
            # PARKING
            # --------------------------------------------------

            car_parking_required=(
                constraints.car_parking_required
            ),

            two_wheeler_parking_required=(
                constraints.two_wheeler_parking_required
            ),

            visitor_parking_required=(
                constraints.visitor_parking_required
            ),

            parking_area_required_m2=(
                constraints.parking_area_required
            ),

            # --------------------------------------------------
            # FIRE / LIFE SAFETY
            # --------------------------------------------------

            fire_access_required=(
                constraints.fire_access_required
            ),

            fire_lift_required=(
                constraints.fire_lift_required
            ),

            fire_staircase_required=(
                constraints.fire_staircase_required
            ),

            minimum_exit_count=(
                constraints.minimum_exit_count
            ),

            minimum_exit_width_m=(
                constraints.minimum_exit_width_m
            ),

            # --------------------------------------------------
            # CIRCULATION
            # --------------------------------------------------

            staircase_count=(
                constraints.staircase_count
            ),

            staircase_width_m=(
                constraints.staircase_width_m
            ),

            corridor_width_m=(
                constraints.corridor_width_m
            ),

            lift_required=(
                constraints.lift_required
            ),

            lift_count=(
                constraints.lift_count
            ),

            # --------------------------------------------------
            # ACCESSIBILITY
            # --------------------------------------------------

            accessible_entrance_required=(
                constraints.accessible_entrance_required
            ),

            ramp_required=(
                constraints.ramp_required
            ),

            ramp_width_m=(
                constraints.ramp_width_m
            ),

            ramp_gradient=(
                constraints.ramp_gradient
            ),

            # --------------------------------------------------
            # OPEN / AMENITY
            # --------------------------------------------------

            recreational_open_space_m2=(
                constraints.recreational_open_space_m2
            ),

            amenity_space_m2=(
                constraints.amenity_space_m2
            ),

            # --------------------------------------------------
            # SPECIAL CONDITIONS
            # --------------------------------------------------

            road_widening=(
                constraints.road_widening
            ),

            reservation_present=(
                constraints.reservation_present
            ),

            # --------------------------------------------------
            # AUDIT / TRACEABILITY
            # --------------------------------------------------

            metadata={
                "project_id": facts.project_id,

                "basic_fsi": constraints.basic_fsi,

                "premium_fsi": constraints.premium_fsi,

                "tdr_fsi": constraints.tdr_fsi,

                "incentive_fsi": constraints.incentive_fsi,

                "total_fsi": constraints.total_fsi,

                "special_height_limit_m": (
                    constraints.special_height_limit_m
                ),

                "applied_rule_count": len(
                    constraints.applied_rules
                ),

                "unresolved_rule_count": len(
                    constraints.unresolved_rules
                ),

                "rejected_rule_count": len(
                    constraints.rejected_rules
                ),

                "warnings": list(
                    constraints.warnings
                ),
            },
        )