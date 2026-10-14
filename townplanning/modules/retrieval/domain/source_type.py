from enum import Enum


class SourceType(str, Enum):
    OCR = "ocr"
    REGULATION = "regulation"
    RULE = "rule"
    TABLE = "table"
    KNOWLEDGE_CARD = "knowledge_card"