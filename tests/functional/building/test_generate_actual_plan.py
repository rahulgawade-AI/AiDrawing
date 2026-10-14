from pathlib import Path

from townplanning.modules.building.generation.architectural_style_plan_generator import (
    ArchitecturalStyleBuildingPlanGenerator,
)


def main():

    # ============================================================
    # ACTUAL PLOT DETECTED FROM YOUR SUPPLIED PLOT IMAGE
    # ============================================================

    plot_coordinates = [
        (0.0, 0.0),
        (24.0, 0.0),
        (24.0, 31.0666667),
        (0.0, 31.0666667),
    ]

    plot_area = 745.6

    # ============================================================
    # PLANNING INPUT
    # ============================================================

    road_width = 12.0

    # IMPORTANT:
    # Keep this equal to the value produced by your
    # regulatory/rule-discovery stage for this test.
    fsi = 2.50

    floors = 5

    # Start with requested 12 units.
    #
    # 3 units/floor × 5 floors = 15 possible units.
    #
    # The generator can subsequently be changed to optimize
    # specifically for exactly 12 units.
    units_per_floor = 3

    # ============================================================
    # GENERATE
    # ============================================================

    output_dir = Path(
        "/tmp/building_plan"
    )

    generator = (
        ArchitecturalStyleBuildingPlanGenerator(
            output_dir=output_dir
        )
    )

    plan = generator.generate(
        plot_coordinates=plot_coordinates,
        plot_area=plot_area,
        road_width=road_width,
        fsi=fsi,
        floors=floors,
        units_per_floor=units_per_floor,
        front_setback=3.0,
        rear_setback=3.0,
        side_setback=1.5,
        unit_mix=[
            "2BHK",
            "2BHK",
            "1BHK",
        ],
    )

    print("=" * 100)
    print("ACTUAL BUILDING PLAN GENERATOR")
    print("=" * 100)

    print()
    print("PLOT AREA:", f"{plot_area:.2f} m²")
    print("ROAD WIDTH:", f"{road_width:.2f} m")
    print("FSI:", fsi)
    print(
        "TARGET FSI AREA:",
        f"{plot_area * fsi:.2f} m²",
    )

    print()
    print("BUILDINGS:", plan.building_count)
    print("FLOORS:", floors)

    for building in plan.buildings:

        print()
        print(
            "BUILDING:",
            building.building_id,
        )

        print(
            "FOOTPRINT:",
            f"{building.width:.2f} × "
            f"{building.depth:.2f} m",
        )

        print(
            "FOOTPRINT AREA:",
            f"{building.footprint_area:.2f} m²",
        )

        print(
            "UNITS/FLOOR:",
            len(building.units),
        )

        for unit in building.units:

            print(
                " ",
                unit.unit_id,
                unit.unit_type,
                f"{unit.area:.2f} m²",
            )

            for room in unit.rooms:

                print(
                    "    ",
                    room.name,
                    f"{room.width:.2f} × "
                    f"{room.depth:.2f} m",
                    f"area={room.area:.2f} m²",
                )

    print()
    print(
        "TOTAL UNITS:",
        plan.total_units,
    )

    print()
    print(
        "OUTPUT:",
        output_dir,
    )

    print()
    print("FILES:")

    for path in sorted(
        output_dir.iterdir()
    ):
        print(
            " -",
            path.name,
        )

    print()
    print(
        "PLAN GENERATION SUCCESSFUL"
    )


if __name__ == "__main__":
    main()
