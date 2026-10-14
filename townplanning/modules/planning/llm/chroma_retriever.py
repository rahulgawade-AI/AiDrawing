from __future__ import annotations

from typing import Any


class ChromaRegulationRetriever:
    """
    ChromaDB semantic retrieval layer.

    Purpose:
        Retrieve only the regulatory evidence relevant to the
        current planning project.

    ChromaDB is NOT the authority for applicability.
    PostgreSQL / deterministic filtering remains authoritative.

    ChromaDB is used to reduce the amount of regulatory text
    sent to Gemma.
    """

    def __init__(
        self,
        client=None,
        collection_name: str = "udcpr",
        embedding_function=None,
    ):
        self.client = client
        self.collection_name = collection_name
        self.embedding_function = embedding_function

        self.collection = None

        if self.client is not None:
            self._load_collection()

    # ==========================================================
    # COLLECTION
    # ==========================================================

    def _load_collection(self):

        try:
            self.collection = (
                self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                )
            )
            return

        except Exception:
            pass

        try:
            self.collection = (
                self.client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                )
            )

        except Exception:
            self.collection = None

    # ==========================================================
    # SEARCH
    # ==========================================================

    def search(
        self,
        query: str,
        *,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:

        if self.collection is None:
            return []

        if not query.strip():
            return []

        kwargs = {
            "query_texts": [query],
            "n_results": n_results,
        }

        if where:
            kwargs["where"] = where

        try:
            result = self.collection.query(
                **kwargs
            )
        except Exception:
            return []

        return self._normalize_result(
            result
        )

    # ==========================================================
    # MULTI QUERY
    # ==========================================================

    def search_many(
        self,
        queries: list[str],
        *,
        n_results_per_query: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:

        results = []

        seen = set()

        for query in queries:

            matches = self.search(
                query,
                n_results=n_results_per_query,
                where=where,
            )

            for item in matches:

                key = (
                    item.get("id")
                    or (
                        item.get("metadata", {})
                        .get("source")
                    )
                    or item.get("text", "")[:200]
                )

                key = str(key)

                if key in seen:
                    continue

                seen.add(key)
                results.append(item)

        return results

    # ==========================================================
    # PROJECT SEARCH
    # ==========================================================

    def search_for_project(
        self,
        facts: dict[str, Any],
        *,
        n_results_per_query: int = 5,
    ) -> list[dict[str, Any]]:

        queries = self._build_queries(
            facts
        )

        results = self.search_many(
            queries,
            n_results_per_query=n_results_per_query,
        )

        return results

    # ==========================================================
    # QUERY GENERATION
    # ==========================================================

    def _build_queries(
        self,
        facts: dict[str, Any],
    ) -> list[str]:

        city = facts.get(
            "city",
            ""
        )

        district = facts.get(
            "district",
            ""
        )

        state = facts.get(
            "state",
            ""
        )

        authority = facts.get(
            "planning_authority",
            ""
        )

        building_type = facts.get(
            "building_type",
            ""
        )

        building_use = facts.get(
            "building_use",
            ""
        )

        road_width = facts.get(
            "road_width",
            facts.get(
                "road_width_m",
                ""
            ),
        )

        plot_area = facts.get(
            "plot_area",
            facts.get(
                "plot_area_sq_m",
                ""
            ),
        )

        group_housing = facts.get(
            "group_housing",
            False,
        )

        base = " ".join(
            str(value)
            for value in (
                city,
                district,
                state,
                authority,
                building_type,
                building_use,
            )
            if value
        )

        queries = []

        # ------------------------------------------------------
        # FSI
        # ------------------------------------------------------

        queries.append(
            f"{base} FSI permissible FSI "
            f"plot area {plot_area} square metres "
            f"road width {road_width} metres"
        )

        queries.append(
            f"{base} basic FSI premium FSI "
            f"TDR incentive FSI maximum FSI"
        )

        # ------------------------------------------------------
        # SETBACK / MARGINS
        # ------------------------------------------------------

        queries.append(
            f"{base} front rear side setback "
            f"margin road width {road_width}"
        )

        # ------------------------------------------------------
        # HEIGHT
        # ------------------------------------------------------

        queries.append(
            f"{base} building height "
            f"number of floors storeys"
        )

        # ------------------------------------------------------
        # FIRE
        # ------------------------------------------------------

        queries.append(
            f"{base} fire safety fire access "
            f"fire tender staircase refuge"
        )

        queries.append(
            f"{base} fire lift building height"
        )

        # ------------------------------------------------------
        # LIFT
        # ------------------------------------------------------

        queries.append(
            f"{base} lift elevator "
            f"lift requirement residential building"
        )

        # ------------------------------------------------------
        # STAIRCASE
        # ------------------------------------------------------

        queries.append(
            f"{base} staircase width "
            f"staircase residential apartment"
        )

        # ------------------------------------------------------
        # PARKING
        # ------------------------------------------------------

        queries.append(
            f"{base} parking car parking "
            f"two wheeler visitor parking"
        )

        # ------------------------------------------------------
        # ACCESSIBILITY
        # ------------------------------------------------------

        queries.append(
            f"{base} accessibility disabled persons "
            f"ramp accessible entrance"
        )

        # ------------------------------------------------------
        # LIGHT / VENTILATION
        # ------------------------------------------------------

        queries.append(
            f"{base} natural light ventilation "
            f"duct shaft"
        )

        # ------------------------------------------------------
        # OPEN SPACE
        # ------------------------------------------------------

        queries.append(
            f"{base} open space recreation "
            f"amenity space"
        )

        # ------------------------------------------------------
        # SANITATION
        # ------------------------------------------------------

        queries.append(
            f"{base} residential sanitation "
            f"water closet drainage"
        )

        # ------------------------------------------------------
        # GROUP HOUSING
        # ------------------------------------------------------

        if group_housing:

            queries.append(
                f"{base} group housing "
                f"common open space amenity"
            )

            queries.append(
                f"{base} group housing "
                f"building separation distance"
            )

        # Remove duplicates.
        unique = []

        seen = set()

        for query in queries:

            key = query.lower().strip()

            if key in seen:
                continue

            seen.add(key)
            unique.append(query)

        return unique

    # ==========================================================
    # RESULT NORMALIZATION
    # ==========================================================

    @staticmethod
    def _normalize_result(
        result: dict[str, Any],
    ) -> list[dict[str, Any]]:

        if not result:
            return []

        ids = result.get(
            "ids",
            [[]],
        )

        documents = result.get(
            "documents",
            [[]],
        )

        metadatas = result.get(
            "metadatas",
            [[]],
        )

        distances = result.get(
            "distances",
            [[]],
        )

        ids = (
            ids[0]
            if ids
            else []
        )

        documents = (
            documents[0]
            if documents
            else []
        )

        metadatas = (
            metadatas[0]
            if metadatas
            else []
        )

        distances = (
            distances[0]
            if distances
            else []
        )

        output = []

        for index, item_id in enumerate(ids):

            document = (
                documents[index]
                if index < len(documents)
                else ""
            )

            metadata = (
                metadatas[index]
                if index < len(metadatas)
                else {}
            )

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            output.append(
                {
                    "id": item_id,
                    "text": document or "",
                    "metadata": metadata or {},
                    "distance": distance,
                }
            )

        return output