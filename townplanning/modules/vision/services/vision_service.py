from __future__ import annotations

from pathlib import Path

from townplanning.modules.vision.domain.drawing import Drawing
from townplanning.modules.vision.domain.spatial_context import (
    SpatialContext,
)

from townplanning.modules.vision.parsers.image_parser import (
    ImageParser,
)
from townplanning.modules.vision.parsers.pdf_parser import (
    PDFParser,
)

from townplanning.modules.vision.preprocessing.image_loader import (
    ImageLoader,
)
from townplanning.modules.vision.preprocessing.image_analyzer import (
    ImageAnalyzer,
)
from townplanning.modules.vision.preprocessing.preprocess_pipeline import (
    PreprocessPipeline,
)

from townplanning.modules.vision.ocr.ocr_service import (
    OCRService,
)

from townplanning.modules.vision.geometry.geometry_service import (
    GeometryService,
)

from townplanning.modules.vision.detectors.plot_detector import (
    PlotDetector,
)
from townplanning.modules.vision.detectors.road_detector import (
    RoadDetector,
)
from townplanning.modules.vision.detectors.north_detector import (
    NorthDetector,
)
from townplanning.modules.vision.detectors.scale_detector import (
    ScaleDetector,
)

from townplanning.modules.vision.mappers.text_mapper import (
    TextMapper,
)
from townplanning.modules.vision.mappers.road_mapper import (
    RoadMapper,
)
from townplanning.modules.vision.mappers.plot_mapper import (
    PlotMapper,
)
from townplanning.modules.vision.mappers.north_mapper import (
    NorthMapper,
)
from townplanning.modules.vision.mappers.scale_mapper import (
    ScaleMapper,
)
from townplanning.modules.vision.mappers.spatial_context_builder import (
    SpatialContextBuilder,
)

from townplanning.modules.vision.spatial.spatial_mapper import (
    SpatialMapper,
)

from townplanning.modules.vision.ai.road_ai_detector import (
    AIRoadDetector,
)
from townplanning.modules.vision.ai.road_ai_mapper import (
    RoadAIMapper,
)
from townplanning.modules.vision.services.general_vision_service import (
    GeneralVisionService,
)


class VisionService:
    """
    Entry point for the Vision module.

    Pipeline:

        Image
          |
          +--> Preprocessing --> OCR
          |                       |
          |                       +--> Text
          |                       +--> Dimensions
          |                       +--> Scale
          |                       +--> Plot Area
          |                       +--> Plot Number
          |
          +--> Geometry
          |
          +--> Plot Detection
          |
          +--> Classical Road Detection
          |
          +--> Ollama Road Detection
          |
          +--> North Detection
          |
          +--> SpatialContext
          |
          +--> Spatial Association
    """

    def __init__(self):

        #
        # --------------------------------------------------
        # Parsers
        # --------------------------------------------------
        #

        self._image_parser = ImageParser()

        self._pdf_parser = PDFParser()

        #
        # --------------------------------------------------
        # Preprocessing
        # --------------------------------------------------
        #

        self.loader = ImageLoader()

        self.analyzer = ImageAnalyzer()

        self.preprocess = PreprocessPipeline()

        #
        # --------------------------------------------------
        # OCR
        # --------------------------------------------------
        #

        self.ocr = OCRService()

        #
        # --------------------------------------------------
        # Geometry
        # --------------------------------------------------
        #

        self.geometry = GeometryService()

        #
        # --------------------------------------------------
        # Classical detectors
        # --------------------------------------------------
        #

        self.plot_detector = PlotDetector()

        self.road_detector = RoadDetector()

        self.north_detector = NorthDetector()

        self.scale_detector = ScaleDetector()

        #
        # --------------------------------------------------
        # Mappers
        # --------------------------------------------------
        #

        self.text_mapper = TextMapper()

        self.road_mapper = RoadMapper()

        self.plot_mapper = PlotMapper()

        self.north_mapper = NorthMapper()

        self.scale_mapper = ScaleMapper()

        #
        # --------------------------------------------------
        # Context builder
        # --------------------------------------------------
        #

        self.builder = SpatialContextBuilder()

        #
        # --------------------------------------------------
        # Spatial association
        # --------------------------------------------------
        #

        self.spatial = SpatialMapper()

        #
        # --------------------------------------------------
        # AI road detection
        # --------------------------------------------------
        #

        self.road_ai_detector = AIRoadDetector()

        self.road_ai_mapper = RoadAIMapper()

        self.general_vision = GeneralVisionService()

    # ======================================================
    # DOCUMENT LOADING
    # ======================================================

    def load_document(
        self,
        file_path: str | Path,
    ) -> Drawing:

        path = Path(file_path)

        suffix = path.suffix.lower()

        if suffix == ".pdf":

            return self._pdf_parser.parse(
                path
            )

        if suffix in (
            ".png",
            ".jpg",
            ".jpeg",
            ".bmp",
            ".tif",
            ".tiff",
        ):

            return self._image_parser.parse(
                path
            )

        raise ValueError(
            f"Unsupported document type: {suffix}"
        )

    # ======================================================
    # MAIN PROCESSING PIPELINE
    # ======================================================

    def process(
        self,
        image_path: str | Path,
    ) -> SpatialContext:

        #
        # --------------------------------------------------
        # 1. Load original image
        # --------------------------------------------------
        #

        image = self.loader.load(image_path)

        processed = self.preprocess.process(
            image
        )

        #
        # --------------------------------------------------
        # 4. Calculate coordinate transformation
        #
        # OCR operates on the processed image.
        #
        # Plot/geometry operate on the original image.
        #
        # Therefore convert OCR coordinates back
        # into original-image coordinates.
        # --------------------------------------------------
        #

        original_height, original_width = (
            image.shape[:2]
        )

        ocr_height, ocr_width = (
            processed.shape[:2]
        )

        coordinate_scale_x = (
            original_width / ocr_width
        )

        coordinate_scale_y = (
            original_height / ocr_height
        )

        #
        # Optional diagnostic information.
        #

        # print(
        #     "IMAGE SIZE:",
        #     f"{original_width}x{original_height}",
        # )

        # print(
        #     "OCR IMAGE SIZE:",
        #     f"{ocr_width}x{ocr_height}",
        # )

        # print(
        #     "OCR -> IMAGE SCALE:",
        #     f"x={coordinate_scale_x:.6f}",
        #     f"y={coordinate_scale_y:.6f}",
        # )

        #
        # --------------------------------------------------
        # 5. OCR
        #
        # OCRService returns:
        #
        #   texts
        #   dimensions
        #   scale
        #   area
        #   plot_number
        #
        # Coordinates are normalized inside OCRService.
        # --------------------------------------------------
        #

        (
            texts,
            dimensions,
            scale,
            area,
            plot_number,
        ) = self.ocr.process(
            processed,
            coordinate_scale_x=coordinate_scale_x,
            coordinate_scale_y=coordinate_scale_y,
        )

        ocr_text = "\n".join(
        getattr(text, "text", "")
        for text in texts
        if getattr(text, "text", None)
        )
        general_evidence = self.general_vision.analyze(
        image_path=image_path,
        ocr_text=ocr_text,
    )

        #
        # --------------------------------------------------
        # 6. Geometry
        #
        # GeometryService only accepts the image.
        #
        # Do NOT pass coordinate_scale_x/y here.
        # --------------------------------------------------
        #

        geometry = self.geometry.process(
            processed
        )

        #
        # Keep the result available for future
        # geometry integration.
        #
        _ = geometry

        #
        # --------------------------------------------------
        # 7. Load document/domain representation
        # --------------------------------------------------
        #

        drawing = self.load_document(
            image_path
        )

        #
        # --------------------------------------------------
        # 8. Plot boundary detection
        #
        # IMPORTANT:
        # Use ORIGINAL image, not processed image.
        # Plot geometry is therefore in original
        # image coordinates.
        # --------------------------------------------------
        #

        plot = self.plot_detector.detect(
    drawing=drawing,
    image=image,
    image_path=image_path,
    texts=texts,
    dimensions=dimensions,
)

        # print(
        #     "PLOT DETECTOR:",
        #     plot,
        # )

        #
        # --------------------------------------------------
        # 9. Classical road detection
        # --------------------------------------------------
        #

        classical_roads = (
            self.road_detector.detect(
                drawing
            )
        )

        #
        # --------------------------------------------------
        # 10. AI road detection
        #
        # Ollama receives the original image/path.
        # --------------------------------------------------
        #

        ai_road_detections = (
            self.road_ai_detector.detect(
                image_path
            )
        )

        # print()
        # print("=" * 100)
        # print("AI ROAD DETECTIONS")
        # print("=" * 100)

        # for detection in ai_road_detections:
        #     print(detection)

        ai_roads = (
            self.road_ai_mapper.map(
                ai_road_detections
            )
        )


        # print()
        # print("=" * 100)
        # print("AI MAPPED ROADS")
        # print("=" * 100)
        
        # for road in ai_roads:
        #     print(road)
        #     print("  width:", road.width)
        #     print("  location:", road.remarks)
        #     print("  metadata:", road.metadata)



        texts = self.text_mapper.map(
                    texts
                )
        #
        # --------------------------------------------------
        # 11. Combine road detections
        # --------------------------------------------------
        #



        roads = (
            classical_roads
            + ai_roads
        )

        #
        # --------------------------------------------------
        # 12. North detection
        #
        # Keep a single detector call.
        # --------------------------------------------------
        #

        north = (
            self.north_detector.detect(
                drawing,
                 texts=texts,
            )
        )

        #
        # --------------------------------------------------
        # 13. Text mapper
        # --------------------------------------------------
        #

        

        #
        # --------------------------------------------------
        # 14. Road mapper
        # --------------------------------------------------
        #

        roads = self.road_mapper.map(
            roads
        )

        #
        # --------------------------------------------------
        # 15. Plot mapper
        # --------------------------------------------------
        #

        plot = self.plot_mapper.map(
            plot
        )

        #
        # --------------------------------------------------
        # 16. North mapper
        # --------------------------------------------------
        #

        north = self.north_mapper.map(
            north
        )

        #
        # --------------------------------------------------
        # 17. Scale mapper
        #
        # OCR already detected the Scale domain object.
        # --------------------------------------------------
        #

        if scale is not None:

            scale = self.scale_mapper.map(
                scale
            )

        #
        # --------------------------------------------------
        # 18. Diagnostic output
        # --------------------------------------------------
        #

        # print(
        #     "OCR TEXT BLOCKS:",
        #     len(texts),
        # )

        # print(
        #     "DIMENSIONS:",
        #     len(dimensions),
        # )

        # print(
        #     "ROADS:",
        #     len(roads),
        # )

        # print(
        #     "SCALE:",
        #     scale,
        # )

        # print(
        #     "PLOT AREA:",
        #     area,
        # )

        # print(
        #     "PLOT NUMBER:",
        #     plot_number,
        # )

        # print(
        #     "NORTH:",
        #     north,
        # )

        #
        # --------------------------------------------------
        # 19. Build SpatialContext
        # --------------------------------------------------
        #

        context = self.builder.build(
            plot=plot,
            roads=roads,
            north=north,
            scale=scale,
            area=area,
            plot_number=plot_number,
            dimensions=dimensions,
            texts=texts,
        )
        context.vision_evidence = general_evidence
        

        #
        # --------------------------------------------------
        # 20. Spatial associations
        # --------------------------------------------------
        #

        context = self.spatial.map(
            context
        )

        #
        # --------------------------------------------------
        # 21. Return final context
        # --------------------------------------------------
        #

        return context
