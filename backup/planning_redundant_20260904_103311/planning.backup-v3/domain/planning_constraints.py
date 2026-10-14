from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .applicable_rule import ApplicableRule


@dataclass(slots=True)
class PlanningConstraints:
    """
    Complete regulatory constraint set for one
    building proposal.

    Values are only populated when supported by
    applicable rules and available facts.
    """

    # --------------------------------------------------
    # Land use
    # --------------------------------------------------

    permitted_uses: list[str] = field(
        default_factory=list
    )

    mixed_use_allowed: bool | None = None

    # --------------------------------------------------
    # FSI
    # --------------------------------------------------

    basic_fsi: float | None = None

    premium_fsi: float | None = None

    tdr_fsi: float | None = None

    incentive_fsi: float | None = None

    maximum_fsi: float | None = None

    total_fsi: float | None = None

    maximum_built_up_area: float | None = None

    # --------------------------------------------------
    # Site coverage / envelope
    # --------------------------------------------------

    maximum_ground_coverage: float | None = None

    front_setback: float | None = None

    rear_setback: float | None = None

    side_setback_left: float | None = None

    side_setback_right: float | None = None

    minimum_open_space: float | None = None

    # --------------------------------------------------
    # Height
    # --------------------------------------------------

    maximum_height_m: float | None = None

    maximum_storeys: int | None = None

    # --------------------------------------------------
    # Parking
    # --------------------------------------------------

    car_parking_required: float | None = None

    two_wheeler_parking_required: float | None = None

    visitor_parking_required: float | None = None

    parking_area_required: float | None = None

    # --------------------------------------------------
    # Fire / life safety
    # --------------------------------------------------

    fire_access_required: bool | None = None

    fire_lift_required: bool | None = None

    fire_staircase_required: bool | None = None

    minimum_exit_count: int | None = None

    minimum_exit_width_m: float | None = None

    # --------------------------------------------------
    # Circulation
    # --------------------------------------------------

    staircase_count: int | None = None

    staircase_width_m: float | None = None

    corridor_width_m: float | None = None

    lift_required: bool | None = None

    lift_count: int | None = None

    # --------------------------------------------------
    # Accessibility
    # --------------------------------------------------

    accessible_entrance_required: bool | None = None

    ramp_required: bool | None = None

    ramp_width_m: float | None = None

    ramp_gradient: float | None = None

    # --------------------------------------------------
    # Open / amenity spaces
    # --------------------------------------------------

    recreational_open_space_m2: float | None = None

    amenity_space_m2: float | None = None

    # --------------------------------------------------
    # Special conditions
    # --------------------------------------------------

    road_widening: bool | None = None

    reservation_present: bool | None = None

    special_height_limit_m: float | None = None

    # --------------------------------------------------
    # Audit
    # --------------------------------------------------

    applied_rules: list[
        ApplicableRule
    ] = field(default_factory=list)

    unresolved_rules: list[
        ApplicableRule
    ] = field(default_factory=list)

    rejected_rules: list[
        ApplicableRule
    ] = field(default_factory=list)

    warnings: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
