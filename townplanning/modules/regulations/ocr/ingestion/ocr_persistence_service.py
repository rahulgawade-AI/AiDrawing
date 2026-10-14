from uuid import uuid4

from townplanning.modules.regulations.domain import Rule
from townplanning.modules.regulations.ocr.domain.ocr_document import OCRDocument


class OCRPersistenceService:
    """
    Persists OCR extracted content as Rule records.

    Each OCR page is stored as a single EXPLANATION rule.
    """

    def __init__(
        self,
        regulation_repository,
        rule_repository,
    ):
        self.regulation_repository = regulation_repository
        self.rule_repository = rule_repository

    def persist(
        self,
        document: OCRDocument,
    ) -> int:

        inserted = 0

        for page in document.pages:

            regulation = self.regulation_repository.get_by_page(
                page.page_number
            )

            if regulation is None:
                continue

            blocks = [
                block
                for block in page.blocks
                if block.text.strip()
            ]

            if not blocks:
                continue

            #
            # Merge page text
            #
            description = "\n\n".join(
                block.text.strip()
                for block in blocks
            )

            #
            # Average confidence
            #
            avg_confidence = (
                sum(block.confidence for block in blocks)
                / len(blocks)
            )

            rule = Rule(

                id=str(uuid4()),

                regulation_id=regulation.id,

                category="EXPLANATION",

                name=f"OCR Explanation - Page {page.page_number}",

                description=description,

                #
                # OCR pages generally don't have structured
                # conditions/results.
                #
                condition={},

                result={},

                priority=999,

                enabled=True,

                metadata={

                    "source": "ocr",

                    "page": page.page_number,

                    "engine": "surya",

                    "confidence": round(avg_confidence, 4),

                    "block_count": len(blocks),
                },
            )

            self.rule_repository.save(rule)

            inserted += 1

        return inserted