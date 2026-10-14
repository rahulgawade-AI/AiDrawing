from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]

VISION_DATA = (
    PROJECT_ROOT
    / "tests"
    / "functional"
    / "vision"
    / "data"
)


def create_hand_drawn_test_image(output: Path) -> None:
    """
    Create a deliberately simple hand-drawn-style planning sketch.

    This is NOT a clean CAD/site-plan input.
    It is used to verify that the generalized vision
    pipeline can handle informal drawings.
    """

    image = Image.new(
        "RGB",
        (1200, 900),
        "white",
    )

    draw = ImageDraw.Draw(image)

    # Irregular hand-drawn-style plot boundary.
    draw.line(
        [
            (180, 200),
            (850, 230),
            (920, 700),
            (140, 650),
            (180, 200),
        ],
        width=5,
    )

    # Road.
    draw.line(
        [
            (100, 780),
            (1050, 780),
        ],
        width=20,
    )

    draw.text(
        (400, 810),
        "ROAD 9M",
        fill="black",
    )

    # Building.
    draw.rectangle(
        [
            (350, 350),
            (700, 600),
        ],
        outline="black",
        width=5,
    )

    draw.text(
        (460, 460),
        "HOUSE",
        fill="black",
    )

    # Plot information.
    draw.text(
        (300, 120),
        "PLOT 500 SQ.M.",
        fill="black",
    )

    draw.text(
        (900, 120),
        "N",
        fill="black",
    )

    image.save(output)


def test_general_vision_technical_images():
    """
    Existing technical images.

    These are useful regression tests, but the generalized
    Vision system must not assume that every image is a
    technical site plan.
    """

    from townplanning.modules.vision.services.general_vision_service import (
        GeneralVisionService,
    )

    images = [
        VISION_DATA / "sample1.png",
        VISION_DATA / "sample2.png",
    ]

    service = GeneralVisionService(
        enable_ai=True,
    )

    for image_path in images:

        assert image_path.exists(), (
            f"Missing test image: {image_path}"
        )

        evidence = service.analyze(
            image_path
        )

        print()
        print("=" * 80)
        print(
            f"GENERAL VISION: {image_path.name}"
        )
        print("=" * 80)

        print(
            "IMAGE TYPE:",
            evidence.image_type,
        )

        print(
            "IMAGE TYPE CONFIDENCE:",
            round(
                evidence.image_type_confidence,
                3,
            ),
        )

        print(
            "IMAGE SIZE:",
            evidence.width,
            "x",
            evidence.height,
        )

        print()
        print("OBSERVATIONS:")

        for observation in evidence.observations:

            print(
                f"  "
                f"{observation.observation_type:30} "
                f"value={str(observation.value):35} "
                f"confidence={observation.confidence:.3f} "
                f"source={observation.source}"
            )

        assert evidence is not None
        assert evidence.width > 0
        assert evidence.height > 0


def test_general_vision_hand_drawn():

    from townplanning.modules.vision.services.general_vision_service import (
        GeneralVisionService,
    )

    output = (
        PROJECT_ROOT
        / "tests"
        / "functional"
        / "vision"
        / "data"
        / "_generated_hand_drawn_test.png"
    )

    try:

        create_hand_drawn_test_image(
            output
        )

        service = GeneralVisionService(
            enable_ai=True,
        )

        evidence = service.analyze(
            output
        )

        print()
        print("=" * 80)
        print("GENERAL VISION: HAND-DRAWN IMAGE")
        print("=" * 80)

        print(
            "IMAGE TYPE:",
            evidence.image_type,
        )

        print(
            "IMAGE TYPE CONFIDENCE:",
            round(
                evidence.image_type_confidence,
                3,
            ),
        )

        print(
            "IMAGE SIZE:",
            evidence.width,
            "x",
            evidence.height,
        )

        print()
        print("OBSERVATIONS:")

        for observation in evidence.observations:

            print(
                f"  "
                f"{observation.observation_type:30} "
                f"value={str(observation.value):35} "
                f"confidence={observation.confidence:.3f} "
                f"source={observation.source}"
            )

        assert evidence is not None
        assert evidence.width == 1200
        assert evidence.height == 900

    finally:

        output.unlink(
            missing_ok=True
        )