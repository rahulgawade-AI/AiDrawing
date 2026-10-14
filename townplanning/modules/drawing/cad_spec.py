from .models import DesignSpecification

def build_cad_payload(design: DesignSpecification) -> dict:
    return {
        "units": "m",
        "site": {
            "plot_area_m2": design.site.plot_area_m2,
            "boundary": design.site.boundary,
            "plot_width_m": design.site.plot_width_m,
            "plot_depth_m": design.site.plot_depth_m,
            "road_width_m": design.site.road_width_m,
            "north_direction": design.site.north_direction,
        },
        "regulatory_envelope": {
            "front_setback_m": design.regulatory.front_setback_m,
            "rear_setback_m": design.regulatory.rear_setback_m,
            "side_setback_left_m": design.regulatory.side_setback_left_m,
            "side_setback_right_m": design.regulatory.side_setback_right_m,
            "maximum_height_m": design.regulatory.maximum_height_m,
            "permissible_fsi": design.regulatory.permissible_fsi,
            "permissible_built_up_area_m2": design.regulatory.permissible_built_up_area_m2,
        },
        "buildings": [b.__dict__ | {"units": [u.__dict__ for u in b.units]} for b in design.buildings],
        "parking": None if not design.parking else design.parking.__dict__,
        "open_space_area_m2": design.open_space_area_m2,
        "amenity_area_m2": design.amenity_area_m2,
    }
