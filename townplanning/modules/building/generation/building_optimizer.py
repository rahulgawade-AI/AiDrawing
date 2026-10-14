from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import List


@dataclass(frozen=True)
class UnitType:
    name: str
    carpet_area_m2: float
    target_ratio: float


@dataclass(frozen=True)
class UnitAllocation:
    unit_type: str
    count: int
    carpet_area_m2: float


@dataclass(frozen=True)
class BuildingOptimization:
    building_count: int
    floors: int
    footprint_area_m2: float
    total_builtup_area_m2: float
    total_units: int
    allocations: List[UnitAllocation]
    unused_fsi_area_m2: float


class BuildingOptimizer:
    """
    Determines a practical residential unit mix from:

        plot area
        permissible FSI
        number of floors
        target carpet areas

    This is an optimization layer.

    It does NOT determine regulations.
    """

    def __init__(
        self,
        efficiency: float = 0.82,
        corridor_core_ratio: float = 0.18,
    ):
        self.efficiency = efficiency
        self.corridor_core_ratio = corridor_core_ratio

    def optimize(
        self,
        plot_area_m2: float,
        maximum_fsi: float,
        floors: int,
        unit_types: List[UnitType],
        building_count: int = 1,
    ) -> BuildingOptimization:

        if plot_area_m2 <= 0:
            raise ValueError("plot_area_m2 must be > 0")

        if maximum_fsi <= 0:
            raise ValueError("maximum_fsi must be > 0")

        if floors <= 0:
            raise ValueError("floors must be > 0")

        if not unit_types:
            raise ValueError("At least one unit type is required.")

        if building_count <= 0:
            raise ValueError("building_count must be > 0")

        # --------------------------------------------------
        # Total permissible FSI area
        # --------------------------------------------------

        maximum_builtup = (
            plot_area_m2 *
            maximum_fsi
        )

        # --------------------------------------------------
        # Ground footprint
        # --------------------------------------------------

        footprint_area = (
            maximum_builtup /
            floors
        )

        footprint_per_building = (
            footprint_area /
            building_count
        )

        # --------------------------------------------------
        # Residential usable carpet area
        #
        # FSI area is NOT equal to carpet area.
        #
        # We reserve circulation/core/services.
        # --------------------------------------------------

        usable_carpet_area = (
            maximum_builtup *
            self.efficiency
        )

        # --------------------------------------------------
        # Allocate units floor-by-floor.
        #
        # We first determine a realistic number of units
        # based on the desired carpet areas.
        # --------------------------------------------------

        allocations = []

        total_units = 0
        remaining = usable_carpet_area

        # Sort larger units first so that the optimizer
        # doesn't consume the whole area with small units.
        ordered = sorted(
            unit_types,
            key=lambda x: x.carpet_area_m2,
            reverse=True,
        )

        # --------------------------------------------------
        # Average target unit area
        # --------------------------------------------------

        weighted_area = sum(
            u.carpet_area_m2 * u.target_ratio
            for u in ordered
        )

        weighted_area = max(
            weighted_area,
            1.0,
        )

        estimated_units = floor(
            usable_carpet_area /
            weighted_area
        )

        if estimated_units <= 0:
            estimated_units = 1

        # --------------------------------------------------
        # Initial ratio-based allocation
        # --------------------------------------------------

        raw_counts = []

        for unit in ordered:

            raw = (
                estimated_units *
                unit.target_ratio
            )

            raw_counts.append(
                max(0, floor(raw))
            )

        # Guarantee at least one of each requested type
        for index in range(len(raw_counts)):

            if (
                ordered[index].target_ratio > 0
                and raw_counts[index] == 0
            ):
                raw_counts[index] = 1

        # --------------------------------------------------
        # Adjust count until it fits the usable area
        # --------------------------------------------------

        def total_area(counts):

            return sum(
                count *
                unit.carpet_area_m2
                for count, unit
                in zip(counts, ordered)
            )

        while total_area(raw_counts) > usable_carpet_area:

            largest_index = max(
                range(len(raw_counts)),
                key=lambda i: (
                    ordered[i].carpet_area_m2
                    if raw_counts[i] > 1
                    else -1
                ),
            )

            if raw_counts[largest_index] <= 1:
                break

            raw_counts[largest_index] -= 1

        # --------------------------------------------------
        # Use remaining area to improve utilization
        # --------------------------------------------------

        while True:

            best_index = None
            best_remaining = None

            current_area = total_area(
                raw_counts
            )

            for index, unit in enumerate(ordered):

                candidate = (
                    current_area +
                    unit.carpet_area_m2
                )

                if candidate <= usable_carpet_area:

                    remainder = (
                        usable_carpet_area -
                        candidate
                    )

                    if (
                        best_remaining is None
                        or remainder <
                        best_remaining
                    ):
                        best_remaining = remainder
                        best_index = index

            if best_index is None:
                break

            raw_counts[best_index] += 1

        # --------------------------------------------------
        # Build allocation result
        # --------------------------------------------------

        for count, unit in zip(
            raw_counts,
            ordered,
        ):

            if count <= 0:
                continue

            allocations.append(
                UnitAllocation(
                    unit_type=unit.name,
                    count=count,
                    carpet_area_m2=unit.carpet_area_m2,
                )
            )

            total_units += count

        allocated_carpet = sum(
            a.count *
            a.carpet_area_m2
            for a in allocations
        )

        return BuildingOptimization(
            building_count=building_count,
            floors=floors,
            footprint_area_m2=footprint_per_building,
            total_builtup_area_m2=maximum_builtup,
            total_units=total_units,
            allocations=allocations,
            unused_fsi_area_m2=(
                maximum_builtup -
                allocated_carpet
            ),
        )