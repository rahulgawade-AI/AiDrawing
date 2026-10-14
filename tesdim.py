from townplanning.modules.vision.ocr.dimension_extractor import DimensionExtractor
from townplanning.modules.vision.domain.bounding_box import BoundingBox

extractor = DimensionExtractor()

box = BoundingBox(
    min_x=100,
    min_y=200,
    max_x=300,
    max_y=230,
)

dimensions = extractor.extract(
    text="22.30",
    bounding_box=box,
    confidence=0.95,
)

for d in dimensions:
    print(d)

