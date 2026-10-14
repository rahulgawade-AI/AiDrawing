from pathlib import Path

from townplanning.modules.vision.preprocessing.image_loader import (
    ImageLoader,
)
from townplanning.modules.vision.preprocessing.image_saver import (
    ImageSaver,
)
from townplanning.modules.vision.preprocessing.preprocess_pipeline import (
    PreprocessPipeline,
)
from townplanning.modules.vision.preprocessing.image_analyzer import (
    ImageAnalyzer,
)


TEST_IMAGE = (
    Path(__file__).parent
    / "data"
    / "sample1.png"
)

OUTPUT_DIR = (
    Path(__file__).parent
    / "output"
)


def main():

    print()
    print("=" * 100)
    print("VISION PREPROCESSING PIPELINE")
    print("=" * 100)

    #
    # Load Image
    #
    print("\n[1] Loading Image...")

    loader = ImageLoader()

    image = loader.load(TEST_IMAGE)

    print(f"    ✓ Loaded : {TEST_IMAGE.name}")
    print(f"    ✓ Shape  : {image.shape}")




    print()

    print("[2] Image Analysis")

    analyzer = ImageAnalyzer()

    analysis = analyzer.analyze(image)

    print(f"    Width          : {analysis.width}")

    print(f"    Height         : {analysis.height}")

    print(f"    Grayscale      : {analysis.grayscale}")

    print(f"    Low Contrast   : {analysis.low_contrast}")

    print(f"    Noisy          : {analysis.noisy}")

    print(f"    Blurred        : {analysis.blurred}")

    print(f"    Resize         : {analysis.needs_resize}")

    print(f"    CLAHE          : {analysis.needs_clahe}")

    print(f"    Deskew         : {analysis.needs_deskew}")






    #
    # Run Pipeline
    #
    print("\n[2] Running Preprocessing Pipeline...")

    pipeline = PreprocessPipeline()

    processed = pipeline.process(image)

    print("    ✓ Pipeline completed")

    #
    # Save Output
    #
    print("\n[3] Saving Output...")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = OUTPUT_DIR / "processed.png"

    saver = ImageSaver()

    saver.save(
        processed,
        output_file,
    )

    print(f"    ✓ Output : {output_file}")

    #
    # Statistics
    #
    print("\n[4] Statistics")

    print(f"    Original Shape  : {image.shape}")
    print(f"    Processed Shape : {processed.shape}")

    #
    # Done
    #
    print("\n" + "=" * 100)
    print("PREPROCESSING PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 100)


if __name__ == "__main__":
    main()