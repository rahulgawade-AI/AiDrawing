class DesignValidator:
    def validate(self, design):
        errors, warnings = [], []
        r = design.regulatory
        if r.permissible_built_up_area_m2 is not None and design.total_built_up_area_m2 > r.permissible_built_up_area_m2 + 1e-6:
            errors.append("Built-up area exceeds permissible built-up area.")
        if r.maximum_built_up_area_m2 is not None and design.total_built_up_area_m2 > r.maximum_built_up_area_m2 + 1e-6:
            errors.append("Built-up area exceeds maximum built-up area.")
        if r.maximum_fsi is not None and design.fsi_used > r.maximum_fsi + 1e-6:
            errors.append("FSI used exceeds maximum FSI.")
        for b in design.buildings:
            if r.maximum_height_m is not None and b.floor_count * design.preferences.floor_height_m > r.maximum_height_m + 1e-6:
                errors.append(f"{b.building_id} exceeds maximum height.")
            if r.lift_required and b.lift_count < (r.lift_count or 1):
                errors.append(f"{b.building_id} has insufficient lifts.")
            if r.fire_lift_required and b.lift_count < (r.fire_lift_count or 1):
                errors.append(f"{b.building_id} has insufficient fire lifts.")
            if r.fire_staircase_required and b.staircase_count < 1:
                errors.append(f"{b.building_id} has no required fire staircase.")
        if design.parking:
            if r.car_parking_required is not None and design.parking.car_spaces < r.car_parking_required:
                errors.append("Car parking is below requirement.")
            if r.two_wheeler_parking_required is not None and design.parking.two_wheeler_spaces < r.two_wheeler_parking_required:
                errors.append("Two-wheeler parking is below requirement.")
        return {"status": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings}
