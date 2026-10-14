from __future__ import annotations
import math
from .geometry import rectangular_buildable_area
from .models import BuildingDesign, DesignSpecification
from .parking import estimate_parking

class DesignOptimizer:
    def __init__(self, site, regulatory, preferences, unit_mix):
        self.site = site
        self.regulatory = regulatory
        self.preferences = preferences
        self.unit_mix = unit_mix

    def optimize(self) -> DesignSpecification:
        if self.site.plot_area_m2 is None:
            raise ValueError("plot_area_m2 is required.")
        if self.regulatory.maximum_height_m is None:
            raise ValueError("maximum_height_m is required.")
        max_storeys = max(1, math.floor(
            self.regulatory.maximum_height_m / self.preferences.floor_height_m
        ))

        ground = rectangular_buildable_area(
            self.site.plot_width_m, self.site.plot_depth_m,
            self.regulatory.front_setback_m, self.regulatory.rear_setback_m,
            self.regulatory.side_setback_left_m, self.regulatory.side_setback_right_m,
        )
        if ground is None:
            raise ValueError(
                "Actual plot geometry or rectangular dimensions plus all applicable "
                "setbacks are required before generating building geometry."
            )
        if ground <= 0:
            raise ValueError(
                "Setbacks leave no positive buildable site area."
            )

        builtup_limits = [
            value
            for value in (
                self.regulatory.permissible_built_up_area_m2,
                self.regulatory.maximum_built_up_area_m2,
            )
            if value is not None
        ]
        fsi_caps = [
            value
            for value in (
                self.regulatory.permissible_fsi,
                self.regulatory.maximum_fsi,
            )
            if value is not None
        ]
        builtup_limits.extend(
            self.site.plot_area_m2 * value for value in fsi_caps
        )
        builtup_limit = min(builtup_limits) if builtup_limits else None
        if builtup_limit is None:
            raise ValueError("Deterministic permissible built-up area/FSI is required.")

        requested_units = sum(u.count for u in self.unit_mix)
        buildings = self.preferences.requested_buildings or 1
        buildings = max(1, min(buildings, max(1, requested_units)))

        per_building = builtup_limit / buildings
        floor_count = max(1, min(max_storeys, math.ceil(per_building / ground)))
        floor_plate = min(ground / buildings, per_building / floor_count)

        result_buildings = []
        remaining_by_type = [u.count for u in self.unit_mix]
        for i in range(buildings):
            units = []
            remaining = sum(remaining_by_type)
            take_total = math.ceil(remaining / (buildings - i))
            left = take_total
            for index, u in enumerate(self.unit_mix):
                take = min(remaining_by_type[index], left)
                if take:
                    units.append(type(u)(u.name, take, u.carpet_area_m2))
                    remaining_by_type[index] -= take
                    left -= take
                if left <= 0:
                    break
            result_buildings.append(BuildingDesign(
                building_id=f"B{i+1}",
                floor_count=floor_count,
                floor_height_m=self.preferences.floor_height_m,
                footprint_m2=floor_plate,
                floor_plate_m2=floor_plate,
                total_floor_area_m2=floor_plate * floor_count,
                units=units,
                lift_count=self.regulatory.lift_count or (1 if self.regulatory.lift_required else 0),
                staircase_count=self.regulatory.staircase_count or (1 if self.regulatory.fire_staircase_required else 1),
                corridor_area_m2=floor_plate * 0.12,
                core_area_m2=floor_plate * 0.08,
            ))

        total = sum(b.total_floor_area_m2 for b in result_buildings)
        parking = estimate_parking(self.regulatory)
        return DesignSpecification(
            site=self.site,
            regulatory=self.regulatory,
            preferences=self.preferences,
            buildings=result_buildings,
            parking=parking,
            open_space_area_m2=self.regulatory.minimum_open_space_m2 or self.regulatory.recreational_open_space_m2 or 0,
            amenity_area_m2=self.regulatory.amenity_space_m2 or 0,
            total_built_up_area_m2=total,
            fsi_used=total / self.site.plot_area_m2,
        )
