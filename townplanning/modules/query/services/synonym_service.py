from __future__ import annotations

import re


class SynonymService:
    """
    Expands common town planning terminology into
    richer search expressions.
    """

    SYNONYMS: dict[str, list[str]] = {

        # ----------------------------------------------------------
        # FSI
        # ----------------------------------------------------------

        "fsi": [
            "floor space index",
            "floor area ratio",
        ],

        # ----------------------------------------------------------
        # Height
        # ----------------------------------------------------------

        "height": [
            "building height",
            "maximum permissible height",
        ],

        # ----------------------------------------------------------
        # Road
        # ----------------------------------------------------------

        "road": [
            "road width",
            "right of way",
        ],

        # ----------------------------------------------------------
        # Plot
        # ----------------------------------------------------------

        "plot": [
            "land parcel",
            "site",
        ],

        # ----------------------------------------------------------
        # Setback
        # ----------------------------------------------------------

        "setback": [
            "building setback",
            "marginal distance",
            "open space",
        ],

        # ----------------------------------------------------------
        # Parking
        # ----------------------------------------------------------

        "parking": [
            "parking requirement",
            "parking spaces",
        ],

        # ----------------------------------------------------------
        # Zone
        # ----------------------------------------------------------

        "zone": [
            "land use zone",
            "planning zone",
        ],

        # ----------------------------------------------------------
        # Premium
        # ----------------------------------------------------------

        "premium": [
            "premium fsi",
            "premium charges",
        ],

        # ----------------------------------------------------------
        # Staircase
        # ----------------------------------------------------------

        "staircase": [
            "fire staircase",
            "escape staircase",
        ],

        # ----------------------------------------------------------
        # Occupancy
        # ----------------------------------------------------------

        "occupancy": [
            "occupancy classification",
            "building use",
        ],
    }

    def expand(
        self,
        query: str,
    ) -> str:
        """
        Expand known planning terms.

        Example
        -------
        Input

            "maximum fsi"

        Output

            "maximum fsi floor space index floor area ratio"
        """

        expanded = query

        lower = query.lower()

        additions: list[str] = []

        for keyword, synonyms in self.SYNONYMS.items():

            if re.search(rf"\b{re.escape(keyword)}\b", lower):

                additions.extend(synonyms)

        if additions:

            expanded += " " + " ".join(additions)

        return expanded

    def get_synonyms(
        self,
        word: str,
    ) -> list[str]:
        """
        Return synonyms for a keyword.
        """

        return self.SYNONYMS.get(
            word.lower(),
            [],
        )