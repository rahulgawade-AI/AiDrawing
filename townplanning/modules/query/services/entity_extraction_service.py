from __future__ import annotations

import re

from townplanning.modules.query.dom.extracted_entity import (
    ExtractedEntity,
)


class EntityExtractionService:
    """
    Extract structured entities from a user query.

    The extractor is deterministic and lightweight.
    """

    ROAD_WIDTH_PATTERN = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(?:m|meter|meters|metre|metres)\b",
        re.IGNORECASE,
    )

    FSI_PATTERN = re.compile(
        r"\bFSI\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?)\b",
        re.IGNORECASE,
    )

    HEIGHT_PATTERN = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(?:m|meter|meters|metre|metres)\s*(?:height|high)?\b",
        re.IGNORECASE,
    )

    AREA_PATTERN = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|sqm|m2|m²|square\s*meters?)\b",
        re.IGNORECASE,
    )

    REGULATION_PATTERN = re.compile(
        r"\b\d+(?:\.\d+){1,5}\b"
    )

    AUTHORITIES = [

        "PMRDA",
        "PMC",
        "PCMC",
        "MMRDA",
        "CIDCO",
        "MIDC",

        "Pune",
        "Mumbai",
        "Nagpur",
        "Nashik",
        "Thane",
        "Aurangabad",
        "Kolhapur",
    ]

    def extract(
        self,
        question: str,
    ) -> list[ExtractedEntity]:
        """
        Extract entities from a query.
        """

        entities: list[ExtractedEntity] = []

        entities.extend(
            self._extract_regulations(question)
        )

        entities.extend(
            self._extract_road_width(question)
        )

        entities.extend(
            self._extract_height(question)
        )

        entities.extend(
            self._extract_area(question)
        )

        entities.extend(
            self._extract_fsi(question)
        )

        entities.extend(
            self._extract_authorities(question)
        )

        return entities

    ####################################################################
    # Regulation
    ####################################################################

    def _extract_regulations(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        return [

            ExtractedEntity(
                entity_type="regulation",
                value=match.group(0),
            )

            for match in self.REGULATION_PATTERN.finditer(text)
        ]

    ####################################################################
    # Road Width
    ####################################################################

    def _extract_road_width(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        entities: list[ExtractedEntity] = []

        lower = text.lower()

        if "road" not in lower:
            return entities

        for match in self.ROAD_WIDTH_PATTERN.finditer(text):

            entities.append(

                ExtractedEntity(

                    entity_type="road_width",

                    value=f"{match.group(1)} m",
                )
            )

        return entities

    ####################################################################
    # Building Height
    ####################################################################

    def _extract_height(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        entities: list[ExtractedEntity] = []

        if "height" not in text.lower():
            return entities

        for match in self.HEIGHT_PATTERN.finditer(text):

            entities.append(

                ExtractedEntity(

                    entity_type="height",

                    value=f"{match.group(1)} m",
                )
            )

        return entities

    ####################################################################
    # Plot Area
    ####################################################################

    def _extract_area(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        return [

            ExtractedEntity(

                entity_type="plot_area",

                value=f"{match.group(1)} sqm",

            )

            for match in self.AREA_PATTERN.finditer(text)
        ]

    ####################################################################
    # FSI Value
    ####################################################################

    def _extract_fsi(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        return [

            ExtractedEntity(

                entity_type="fsi",

                value=match.group(1),

            )

            for match in self.FSI_PATTERN.finditer(text)
        ]

    ####################################################################
    # Authority / City
    ####################################################################

    def _extract_authorities(
        self,
        text: str,
    ) -> list[ExtractedEntity]:

        entities: list[ExtractedEntity] = []

        lower = text.lower()

        for authority in self.AUTHORITIES:

            if authority.lower() in lower:

                entities.append(

                    ExtractedEntity(

                        entity_type="authority",

                        value=authority,
                    )
                )

        return entities