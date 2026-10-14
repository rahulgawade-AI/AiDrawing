from __future__ import annotations

import re


class AcronymService:
    """
    Expands domain-specific acronyms used in
    Town Planning and UDCPR regulations.
    """

    ACRONYMS: dict[str, str] = {

        # ----------------------------------------------------------
        # Core Planning Terms
        # ----------------------------------------------------------

        "FSI": "Floor Space Index",
        "TDR": "Transferable Development Rights",
        "TOD": "Transit Oriented Development",
        "UDCPR": "Unified Development Control and Promotion Regulations",
        "DCR": "Development Control Regulations",
        "GDCR": "General Development Control Regulations",
        "DP": "Development Plan",
        "RP": "Regional Plan",
        "TP": "Town Planning",

        # ----------------------------------------------------------
        # Authorities
        # ----------------------------------------------------------

        "PMRDA": "Pune Metropolitan Region Development Authority",
        "PMC": "Pune Municipal Corporation",
        "PCMC": "Pimpri Chinchwad Municipal Corporation",
        "MMRDA": "Mumbai Metropolitan Region Development Authority",
        "CIDCO": "City and Industrial Development Corporation",
        "MIDC": "Maharashtra Industrial Development Corporation",

        # ----------------------------------------------------------
        # Infrastructure
        # ----------------------------------------------------------

        "MRTS": "Mass Rapid Transit System",
        "BRT": "Bus Rapid Transit",
        "ROW": "Right of Way",

        # ----------------------------------------------------------
        # Fire
        # ----------------------------------------------------------

        "NOC": "No Objection Certificate",

        # ----------------------------------------------------------
        # Buildings
        # ----------------------------------------------------------

        "IT": "Information Technology",
        "ITES": "Information Technology Enabled Services",
        "MSI": "Maximum Space Index",

        # ----------------------------------------------------------
        # Environment
        # ----------------------------------------------------------

        "ESZ": "Eco Sensitive Zone",
        "CRZ": "Coastal Regulation Zone",
    }

    def expand(
        self,
        query: str,
    ) -> str:
        """
        Expand all known acronyms inside a query.

        Example
        -------
        Input:
            "What is FSI in TOD?"

        Output:
            "What is Floor Space Index (FSI)
             in Transit Oriented Development (TOD)?"
        """

        expanded = query

        for acronym, full_name in self.ACRONYMS.items():

            pattern = rf"\b{re.escape(acronym)}\b"

            expanded = re.sub(
                pattern,
                f"{full_name} ({acronym})",
                expanded,
                flags=re.IGNORECASE,
            )

        return expanded

    def is_acronym(
        self,
        word: str,
    ) -> bool:
        """
        Returns True if the supplied word
        is a known acronym.
        """

        return word.upper() in self.ACRONYMS

    def get_expansion(
        self,
        acronym: str,
    ) -> str | None:
        """
        Return the expansion of an acronym.
        """

        return self.ACRONYMS.get(
            acronym.upper(),
        )