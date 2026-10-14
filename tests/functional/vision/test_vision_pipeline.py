from pathlib import Path

from townplanning.modules.vision.services.vision_service import (
    VisionService,
)


TEST_IMAGE = (
    Path(__file__).parent
    / "data"
    / "sample1.png"
)


def main():

    print()
    print("=" * 100)
    print("VISION PIPELINE")
    print("=" * 100)

    vision = VisionService()

    context = vision.process(
        TEST_IMAGE,
    )

    print()

    print("BOUNDARY")
    print("--------------------------------")

    print(context.boundary)

    print()

    print("ROADS")
    print("--------------------------------")

    print(len(context.roads))

    for road in context.roads:

        print(road)

    print()

    print("DIMENSIONS")
    print("--------------------------------")

    print(len(context.dimensions))

    for dimension in context.dimensions:

        print(dimension)

    print()

    print("OCR TEXT")
    print("--------------------------------")

    print(len(context.texts))

    for text in context.texts:

        print(text.text)

    print()

    print("INTERNAL TEXT")
    print("--------------------------------")

    print(len(context.internal_text))

    print()

    print("EXTERNAL TEXT")
    print("--------------------------------")

    print(len(context.external_text))

    print()

    print("EDGE COUNT")
    print("--------------------------------")

    print(len(context.edges))

    print()

    print("EDGE DIMENSIONS")
    print("--------------------------------")

    print(len(context.edge_dimensions))

    print()

    print("EDGE ROADS")
    print("--------------------------------")

    print(len(context.edge_roads))

    print()

    print("NORTH")
    print("--------------------------------")

    print(context.north)

    print()

    print("SCALE")
    print("--------------------------------")

    print(context.scale)

    print()

    print()

    print("PLOT AREA")
    print("--------------------------------")

    print(context.area)

    print()

    print("PLOT NUMBER")
    print("--------------------------------")

    print(context.plot_number)

    print("=" * 100)
    print("VISION PIPELINE PASSED")
    print("=" * 100)


if __name__ == "__main__":
    main()