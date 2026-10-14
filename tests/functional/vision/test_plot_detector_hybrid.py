from pathlib import Path

from townplanning.modules.vision.services.vision_service import (
    VisionService,
)


TEST_IMAGES = [
    Path(__file__).parent / "data" / "sample1.png",
    Path(__file__).parent / "data" / "sample2.png",
]


def test_hybrid_plot_detection():
    vision = VisionService()

    for image in TEST_IMAGES:
        print()
        print("=" * 100)
        print(
            f"HYBRID PLOT DETECTION: {image.name}"
        )
        print("=" * 100)

        drawing = vision.load_document(
            image
        )

        assert drawing is not None

        plot = vision.plot_detector.detect(
            drawing,
            image,
        )

        print()
        print(
            "RESULT:"
        )
        print(
            "Plot:",
            plot,
        )

        assert plot is not None

        assert len(
            plot.vertices
        ) >= 3