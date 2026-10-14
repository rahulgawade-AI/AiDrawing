from __future__ import annotations

import json
from pathlib import Path

from townplanning.modules.building.generation.building_optimizer import (
    BuildingOptimizer,
    UnitType,
)

from townplanning.modules.building.generation.architectural_floor_plan import (
    ArchitecturalFloorPlanGenerator,
)

from townplanning.modules.building.generation.architectural_validator import (
    ArchitecturalValidator,
)

from townplanning.modules.building.generation.architectural_png_renderer import (
    ArchitecturalPNGRenderer,
)


def main():

    output = Path(
        "/tmp/optimized_building_plan"
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ======================================================
    # PROJECT INPUT
    # ======================================================

    plot_area = 745.6

    maximum_fsi = 2.5

    floors = 5

    # ======================================================
    # UNIT TARGETS
    #
    # These are TARGET carpet areas.
    #
    # The optimizer determines how many fit.
    # ======================================================

    unit_types = [

        UnitType(
            name="2BHK",
            carpet_area_m2=85.0,
            target_ratio=0.60,
        ),

        UnitType(
            name="1BHK",
            carpet_area_m2=55.0,
            target_ratio=0.40,
        ),
    ]

    # ======================================================
    # OPTIMIZATION
    # ======================================================

    optimizer = BuildingOptimizer(
        efficiency=0.82,
    )

    result = optimizer.optimize(
        plot_area_m2=plot_area,
        maximum_fsi=maximum_fsi,
        floors=floors,
        unit_types=unit_types,
        building_count=1,
    )

    print("=" * 80)
    print("BUILDING OPTIMIZATION")
    print("=" * 80)

    print()
    print(
        "Plot area:",
        plot_area,
        "m²",
    )

    print(
        "Maximum FSI:",
        maximum_fsi,
    )

    print(
        "Maximum built-up:",
        result.total_builtup_area_m2,
        "m²",
    )

    print(
        "Floors:",
        result.floors,
    )

    print(
        "Building count:",
        result.building_count,
    )

    print(
        "Footprint:",
        result.footprint_area_m2,
        "m²",
    )

    print(
        "Total units:",
        result.total_units,
    )

    print()
    print("UNIT MIX:")

    for allocation in result.allocations:

        print(
            f" - {allocation.unit_type}: "
            f"{allocation.count} × "
            f"{allocation.carpet_area_m2:.1f} m²"
        )

    # ======================================================
    # ARCHITECTURAL GENERATION
    # ======================================================

    generator = (
        ArchitecturalFloorPlanGenerator()
    )

    validator = (
        ArchitecturalValidator()
    )

    renderer = (
        ArchitecturalPNGRenderer()
    )

    unit_counter = 1

    generated_units = []

    for allocation in result.allocations:

        for _ in range(
            allocation.count
        ):

            unit_id = (
                f"U{unit_counter:02d}"
            )

            unit = generator.generate_unit(
                unit_id=unit_id,
                unit_type=allocation.unit_type,
                carpet_area_m2=(
                    allocation.carpet_area_m2
                ),
            )

            # ----------------------------------------------
            # Validate before rendering
            # ----------------------------------------------

            validator.validate(
                unit
            )

            # ----------------------------------------------
            # PNG
            # ----------------------------------------------

            png = output / (
                f"{unit_id}_"
                f"{allocation.unit_type}.png"
            )

            renderer.render(
                unit,
                png,
            )

            generated_units.append(
                {
                    "unit_id": unit_id,
                    "unit_type": allocation.unit_type,
                    "carpet_area_m2": (
                        allocation.carpet_area_m2
                    ),
                    "png": str(png),
                }
            )

            unit_counter += 1

    # ======================================================
    # REPORT
    # ======================================================

    report = {

        "plot_area_m2":
            plot_area,

        "maximum_fsi":
            maximum_fsi,

        "maximum_builtup_area_m2":
            result.total_builtup_area_m2,

        "floors":
            floors,

        "building_count":
            result.building_count,

        "footprint_area_m2":
            result.footprint_area_m2,

        "total_units":
            result.total_units,

        "allocations": [

            {
                "unit_type":
                    allocation.unit_type,

                "count":
                    allocation.count,

                "carpet_area_m2":
                    allocation.carpet_area_m2,
            }

            for allocation
            in result.allocations
        ],

        "units":
            generated_units,
    }

    report_path = (
        output /
        "design_report.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "Output:",
        output,
    )

    print(
        "Report:",
        report_path,
    )

    print()
    print(
        "ARCHITECTURAL GENERATION SUCCESSFUL"
    )


if __name__ == "__main__":
    main()