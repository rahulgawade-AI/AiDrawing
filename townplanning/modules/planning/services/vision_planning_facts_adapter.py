from __future__ import annotations

from dataclasses import fields
from typing import Any

from townplanning.modules.planning.domain.planning_facts import (
    PlanningFacts,
)


class VisionPlanningFactsAdapter:
    """
    Convert Vision SpatialContext into PlanningFacts.

    This adapter transfers OBSERVED information from the Vision
    subsystem into the canonical PlanningFacts model.

    It does NOT perform regulatory interpretation or calculations.

    Vision must NOT calculate or invent:

        - FSI
        - basic FSI
        - premium FSI
        - TDR
        - ancillary FSI
        - permissible FSI
        - setbacks
        - margins
        - parking requirements
        - permissible height
        - fire requirements
        - lift requirements
        - staircase requirements
        - amenity requirements
        - recreational open-space requirements
        - development eligibility

    Those responsibilities remain with the deterministic planning
    / regulatory engine.
    """

    # ------------------------------------------------------------------
    # Fields that this adapter is allowed to populate directly.
    # ------------------------------------------------------------------

    VISION_FIELDS = {
        "plot_number",
        "survey_number",
        "cts_number",
        "plot_area",
        "plot_width",
        "plot_depth",
        "plot_shape",
        "plot_side_lengths",
        "boundary",
        "boundary_geometry",
        "north_direction",
        "road_width",
        "road_widths",
        "road_frontage_count",
        "road_frontages",
        "road_locations",
        "road_type",
        "road_types",
        "road_name",
        "road_names",
    }

    # ------------------------------------------------------------------
    # Regulatory/design fields that Vision must never populate.
    # ------------------------------------------------------------------

    FORBIDDEN_FIELDS = {
        # FSI
        "requested_fsi",
        "basic_fsi",
        "premium_fsi",
        "tdr_fsi",
        "ancillary_fsi",
        "maximum_fsi",
        "permissible_fsi",
        "basic_fsi_area",
        "premium_fsi_area",
        "tdr_fsi_area",
        "ancillary_fsi_area",
        "permissible_built_up_area",
        "maximum_built_up_area",

        # Setbacks / margins
        "front_setback",
        "rear_setback",
        "side_setback_left",
        "side_setback_right",
        "side_margin",
        "rear_margin",
        "front_margin",
        "building_separation",
        "distance_between_buildings",

        # Parking requirements
        "parking_requirement_known",
        "parking_area",
        "parking_floor_area",

        # Regulatory height
        "maximum_requested_height",
        "permissible_height",
        "maximum_height",

        # Fire / life safety
        "fire_noc_required",
        "fire_requirements",
        "fire_access_available",
        "fire_tender_movement_available",
        "fire_tender_access_width",
        "fire_tender_access_distance",

        # Lifts
        "lift_required",
        "lift_count",
        "fire_lift_count",

        # Stairs / exits
        "staircase_count",
        "staircase_required",
        "exit_count",
        "exit_width",

        # Open space / amenity
        "amenity_space_required",
        "recreational_open_space_required",
        "recreational_open_space_required_percent",
        "recreational_open_space_minimum_area",

        # Derived development potential
        "net_plot_area",
        "plotable_area",
        "pro_rata_fsi_factor",
        "development_potential",
    }

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    @classmethod
    def convert(
        cls,
        context: Any,
        facts: PlanningFacts | None = None,
    ) -> PlanningFacts:
        """
        Convert Vision SpatialContext into PlanningFacts.

        Existing non-empty PlanningFacts are preserved.

        This method only transfers information actually observed
        by Vision.
        """

        if facts is None:
            facts = PlanningFacts()

        if context is None:
            return facts

        cls._validate_schema()

        # --------------------------------------------------------------
        # Plot / site identification
        # --------------------------------------------------------------

        cls._map_plot(
            context=context,
            facts=facts,
        )

        # --------------------------------------------------------------
        # Boundary geometry
        # --------------------------------------------------------------

        cls._map_boundary(
            context=context,
            facts=facts,
        )

        # --------------------------------------------------------------
        # Dimensions
        # --------------------------------------------------------------

        cls._map_dimensions(
            context=context,
            facts=facts,
        )

        # --------------------------------------------------------------
        # Roads
        # --------------------------------------------------------------

        cls._map_roads(
            context=context,
            facts=facts,
        )

        # --------------------------------------------------------------
        # North
        # --------------------------------------------------------------

        cls._map_north(
            context=context,
            facts=facts,
        )

        # --------------------------------------------------------------
        # Drawing scale
        # --------------------------------------------------------------

        cls._map_scale(
            context=context,
            facts=facts,
        )

        # --------------------------------------------------------------
        # OCR text
        # --------------------------------------------------------------

        cls._map_text(
            context=context,
            facts=facts,
        )

        # --------------------------------------------------------------
        # Preserve complete SpatialContext.
        #
        # This is intentionally stored in `values` because the
        # complete Vision object is not itself a PlanningFacts field.
        # --------------------------------------------------------------

        facts.values[
            "vision_spatial_context"
        ] = context

        facts.fact_sources[
            "vision_spatial_context"
        ] = "vision"

        return facts

    # ==================================================================
    # PLOT
    # ==================================================================

    @classmethod
    def _map_plot(
        cls,
        context: Any,
        facts: PlanningFacts,
    ) -> None:

        # --------------------------------------------------------------
        # Plot number
        # --------------------------------------------------------------

        plot_number = getattr(
            context,
            "plot_number",
            None,
        )

        if plot_number is not None:

            value = cls._first_value(
                plot_number,
                (
                    "value",
                    "number",
                    "plot_number",
                ),
            )

            if value is not None:

                cls._set_if_missing(
                    facts,
                    "plot_number",
                    str(value),
                )

                cls._record_source(
                    facts,
                    "plot_number",
                    source="vision",
                    confidence=getattr(
                        plot_number,
                        "confidence",
                        None,
                    ),
                    evidence={
                        "value": value,
                        "source": "vision",
                    },
                )

        # --------------------------------------------------------------
        # Plot area
        # --------------------------------------------------------------

        area = getattr(
            context,
            "area",
            None,
        )

        if area is not None:

            metric_value = getattr(
                area,
                "metric_value",
                None,
            )

            if metric_value is None:
                metric_value = getattr(
                    area,
                    "value",
                    None,
                )

            if metric_value is not None:

                cls._set_if_missing(
                    facts,
                    "plot_area",
                    metric_value,
                )

                cls._record_source(
                    facts,
                    "plot_area",
                    source="vision",
                    confidence=getattr(
                        area,
                        "confidence",
                        None,
                    ),
                    evidence={
                        "value": metric_value,
                        "unit": getattr(
                            area,
                            "unit",
                            None,
                        ),
                        "source": "vision",
                    },
                )

        # --------------------------------------------------------------
        # PlotBoundary metadata
        # --------------------------------------------------------------

        boundary = getattr(
            context,
            "boundary",
            None,
        )

        if boundary is None:
            return

        for source_name in (
            "survey_number",
            "cts_number",
        ):

            value = getattr(
                boundary,
                source_name,
                None,
            )

            if value is not None:

                cls._set_if_missing(
                    facts,
                    source_name,
                    value,
                )

                cls._record_source(
                    facts,
                    source_name,
                    source="vision",
                    evidence={
                        "value": value,
                        "source": "vision",
                    },
                )

    # ==================================================================
    # BOUNDARY
    # ==================================================================

    @classmethod
    def _map_boundary(
        cls,
        context: Any,
        facts: PlanningFacts,
    ) -> None:

        plot_boundary = getattr(
            context,
            "boundary",
            None,
        )

        if plot_boundary is None:
            return

        # --------------------------------------------------------------
        # PlanningFacts field is `boundary`, NOT `plot_boundary`.
        #
        # The Vision PlotBoundary object is preserved here.
        # --------------------------------------------------------------

        cls._set_if_missing(
            facts,
            "boundary",
            plot_boundary,
        )

        cls._record_source(
            facts,
            "boundary",
            source="vision",
            evidence={
                "source": "vision",
                "object_type": type(
                    plot_boundary
                ).__name__,
            },
        )

        # --------------------------------------------------------------
        # PlotBoundary.boundary contains the actual geometric
        # representation.
        # --------------------------------------------------------------

        geometry = getattr(
            plot_boundary,
            "boundary",
            None,
        )

        if geometry is not None:

            cls._set_if_missing(
                facts,
                "boundary_geometry",
                geometry,
            )

            cls._record_source(
                facts,
                "boundary_geometry",
                source="vision.geometry",
                evidence={
                    "source": "vision.geometry",
                    "geometry_type": type(
                        geometry
                    ).__name__,
                },
            )

        # --------------------------------------------------------------
        # Determine observed shape.
        #
        # This is geometric classification, not a regulation.
        # --------------------------------------------------------------

        segments = list(
            getattr(
                geometry,
                "segments",
                [],
            )
            or []
        )

        shape = cls._classify_boundary_shape(
            plot_boundary,
            segments,
        )

        if shape is not None:

            cls._set_if_missing(
                facts,
                "plot_shape",
                shape,
            )

            cls._record_source(
                facts,
                "plot_shape",
                source="vision.geometry",
                evidence={
                    "source": "vision.geometry",
                    "shape": shape,
                    "segment_count": len(
                        segments
                    ),
                },
            )

    # ==================================================================
    # DIMENSIONS
    # ==================================================================

    @classmethod
    def _map_dimensions(
        cls,
        context: Any,
        facts: PlanningFacts,
    ) -> None:

        dimensions = list(
            getattr(
                context,
                "dimensions",
                [],
            )
            or []
        )

        # --------------------------------------------------------------
        # Preserve all dimension observations.
        # --------------------------------------------------------------

        detected_dimensions = []

        for dimension in dimensions:

            detected_dimensions.append(
                cls._dimension_record(
                    dimension
                )
            )

        if detected_dimensions:

            facts.values[
                "detected_dimensions"
            ] = detected_dimensions

            cls._record_source(
                facts,
                "detected_dimensions",
                source="vision.ocr",
                evidence={
                    "source": "vision.ocr",
                    "count": len(
                        detected_dimensions
                    ),
                },
            )

        # --------------------------------------------------------------
        # Existing Vision edge associations.
        #
        # Vision has already associated dimension annotations with
        # boundary edges. Preserve those associations instead of
        # trying to rediscover them.
        # --------------------------------------------------------------

        edge_dimensions = list(
            getattr(
                context,
                "edge_dimensions",
                [],
            )
            or []
        )

        if not edge_dimensions:
            return

        associations = []

        for item in edge_dimensions:

            if not isinstance(
                item,
                (tuple, list),
            ):
                continue

            if len(item) < 2:
                continue

            dimension = item[0]
            edge = item[1]

            associations.append(
                {
                    "dimension": cls._dimension_record(
                        dimension
                    ),
                    "edge": cls._geometry_repr(
                        edge
                    ),
                }
            )

        if not associations:
            return

        facts.values[
            "plot_dimension_edge_associations"
        ] = associations

        cls._record_source(
            facts,
            "plot_dimension_edge_associations",
            source="vision.geometry",
            evidence={
                "source": "vision.geometry",
                "count": len(
                    associations
                ),
            },
        )

        # --------------------------------------------------------------
        # Build side-length dictionary only when a boundary edge has
        # exactly ONE associated dimension.
        #
        # This is important for your sample:
        #
        # left edge has:
        #     17.8 m
        #     6.25 m
        #
        # Therefore we must NOT arbitrarily choose one as the complete
        # side length.
        # --------------------------------------------------------------

        side_lengths = cls._build_unambiguous_side_lengths(
            context=context,
            edge_dimensions=edge_dimensions,
        )

        if side_lengths:

            cls._set_if_missing(
                facts,
                "plot_side_lengths",
                side_lengths,
            )

            cls._record_source(
                facts,
                "plot_side_lengths",
                source="vision.geometry",
                evidence={
                    "source": "vision.geometry",
                    "method": "unambiguous_edge_dimension",
                    "values": side_lengths,
                },
            )

        # --------------------------------------------------------------
        # Width/depth are intentionally NOT inferred from arbitrary
        # dimensions.
        #
        # Example:
        #
        #     22.3 m
        #     17.8 m
        #     20.15 m
        #     32.6 m
        #
        # does NOT prove which one is "width" and which one is
        # "depth".
        #
        # Those remain missing until survey/user/GIS information
        # provides the semantic meaning.
        # --------------------------------------------------------------

    # ==================================================================
    # ROADS
    # ==================================================================

    @classmethod
    def _map_roads(
        cls,
        context: Any,
        facts: PlanningFacts,
    ) -> None:

        roads = list(
            getattr(
                context,
                "roads",
                [],
            )
            or []
        )

        # No roads detected is a valid Vision result.
        if not roads:
            return

        road_records = []

        widths = []
        names = []
        types = []

        for road in roads:

            width = getattr(
                road,
                "width",
                None,
            )

            name = getattr(
                road,
                "name",
                None,
            )

            road_type = getattr(
                road,
                "road_type",
                None,
            )

            record = {
                "name": name,
                "width": width,
                "unit": getattr(
                    road,
                    "unit",
                    None,
                ),
                "road_type": road_type,
                "remarks": getattr(
                    road,
                    "remarks",
                    None,
                ),
                "centerline": cls._geometry_repr(
                    getattr(
                        road,
                        "centerline",
                        None,
                    )
                ),
                "metadata": getattr(
                    road,
                    "metadata",
                    {},
                ),
            }

            road_records.append(
                record
            )

            if width is not None:
                widths.append(
                    width
                )

            if name:
                names.append(
                    name
                )

            if road_type:
                types.append(
                    road_type
                )

        # --------------------------------------------------------------
        # Preserve raw detected roads.
        # --------------------------------------------------------------

        facts.values[
            "detected_roads"
        ] = road_records

        cls._record_source(
            facts,
            "detected_roads",
            source="vision",
            evidence={
                "source": "vision",
                "count": len(
                    road_records
                ),
            },
        )

        # --------------------------------------------------------------
        # Road widths
        # --------------------------------------------------------------

        if widths:

            cls._set_if_missing(
                facts,
                "road_widths",
                widths,
            )

            cls._record_source(
                facts,
                "road_widths",
                source="vision",
                evidence={
                    "source": "vision",
                    "values": widths,
                },
            )

            if len(widths) == 1:

                cls._set_if_missing(
                    facts,
                    "road_width",
                    widths[0],
                )

                cls._record_source(
                    facts,
                    "road_width",
                    source="vision",
                    evidence={
                        "source": "vision",
                        "value": widths[0],
                    },
                )

        # --------------------------------------------------------------
        # Road names
        # --------------------------------------------------------------

        if names:

            cls._set_if_missing(
                facts,
                "road_names",
                names,
            )

            cls._record_source(
                facts,
                "road_names",
                source="vision",
                evidence={
                    "source": "vision",
                    "values": names,
                },
            )

            if len(names) == 1:

                cls._set_if_missing(
                    facts,
                    "road_name",
                    names[0],
                )

                cls._record_source(
                    facts,
                    "road_name",
                    source="vision",
                )

        # --------------------------------------------------------------
        # Road types
        # --------------------------------------------------------------

        if types:

            cls._set_if_missing(
                facts,
                "road_types",
                types,
            )

            cls._record_source(
                facts,
                "road_types",
                source="vision",
                evidence={
                    "source": "vision",
                    "values": types,
                },
            )

            if len(types) == 1:

                cls._set_if_missing(
                    facts,
                    "road_type",
                    types[0],
                )

                cls._record_source(
                    facts,
                    "road_type",
                    source="vision",
                )

        # --------------------------------------------------------------
        # Edge → road associations
        # --------------------------------------------------------------

        edge_roads = list(
            getattr(
                context,
                "edge_roads",
                [],
            )
            or []
        )

        if edge_roads:

            edge_road_records = []

            for item in edge_roads:

                edge_road_records.append(
                    cls._geometry_repr(
                        item
                    )
                )

            facts.values[
                "vision_edge_roads"
            ] = edge_road_records

            cls._record_source(
                facts,
                "vision_edge_roads",
                source="vision.geometry",
                evidence={
                    "source": "vision.geometry",
                    "count": len(
                        edge_road_records
                    ),
                },
            )

            # Only count actual edge-road associations.
            cls._set_if_missing(
                facts,
                "road_frontage_count",
                len(edge_road_records),
            )

            cls._record_source(
                facts,
                "road_frontage_count",
                source="vision.geometry",
                evidence={
                    "source": "vision.geometry",
                    "count": len(
                        edge_road_records
                    ),
                },
            )

    # ==================================================================
    # NORTH
    # ==================================================================

    @classmethod
    def _map_north(
        cls,
        context: Any,
        facts: PlanningFacts,
    ) -> None:

        north = getattr(
            context,
            "north",
            None,
        )

        if north is None:
            return

        angle = getattr(
            north,
            "angle",
            None,
        )

        if angle is None:

            angle = getattr(
                north,
                "bearing",
                None,
            )

        if angle is None:
            return

        cls._set_if_missing(
            facts,
            "north_direction",
            angle,
        )

        cls._record_source(
            facts,
            "north_direction",
            source="vision",
            confidence=getattr(
                north,
                "confidence",
                None,
            ),
            evidence={
                "source": "vision",
                "angle": angle,
                "detected_text": getattr(
                    north,
                    "detected_text",
                    None,
                ),
                "source_type": getattr(
                    north,
                    "source",
                    None,
                ),
            },
        )

    # ==================================================================
    # SCALE
    # ==================================================================

    @classmethod
    def _map_scale(
        cls,
        context: Any,
        facts: PlanningFacts,
    ) -> None:

        scale = getattr(
            context,
            "scale",
            None,
        )

        if scale is None:
            return

        scale_string = str(
            scale
        )

        facts.values[
            "drawing_scale"
        ] = scale_string

        cls._record_source(
            facts,
            "drawing_scale",
            source="vision.ocr",
            evidence={
                "source": "vision.ocr",
                "numerator": getattr(
                    scale,
                    "numerator",
                    None,
                ),
                "denominator": getattr(
                    scale,
                    "denominator",
                    None,
                ),
            },
        )

    # ==================================================================
    # OCR TEXT
    # ==================================================================

    @classmethod
    def _map_text(
        cls,
        context: Any,
        facts: PlanningFacts,
    ) -> None:

        texts = list(
            getattr(
                context,
                "texts",
                [],
            )
            or []
        )

        if not texts:
            return

        records = []

        for text in texts:

            records.append(
                {
                    "text": getattr(
                        text,
                        "text",
                        None,
                    ),
                    "confidence": getattr(
                        text,
                        "confidence",
                        None,
                    ),
                    "bounding_box": cls._geometry_repr(
                        getattr(
                            text,
                            "bounding_box",
                            None,
                        )
                    ),
                }
            )

        facts.values[
            "vision_text"
        ] = records

        cls._record_source(
            facts,
            "vision_text",
            source="vision.ocr",
            evidence={
                "source": "vision.ocr",
                "count": len(records),
            },
        )

    # ==================================================================
    # SIDE LENGTHS
    # ==================================================================

    @classmethod
    def _build_unambiguous_side_lengths(
        cls,
        context: Any,
        edge_dimensions: list[Any],
    ) -> dict[str, float]:

        """
        Build PlanningFacts.plot_side_lengths.

        Only an edge with exactly one dimension annotation is included.

        This prevents an annotation such as 6.25 m from incorrectly
        replacing 17.8 m on the same boundary edge.
        """

        edges = list(
            getattr(
                context,
                "edges",
                [],
            )
            or []
        )

        if not edges:
            return {}

        edge_records: dict[
            int,
            list[float]
        ] = {
            index: []
            for index in range(
                len(edges)
            )
        }

        # --------------------------------------------------------------
        # Match each dimension edge to the Vision boundary edge.
        #
        # In the current Vision output these are LineString objects.
        # WKT comparison is sufficient because the same geometry object
        # representation is being associated by the Vision pipeline.
        # --------------------------------------------------------------

        edge_keys = {}

        for index, edge in enumerate(edges):

            edge_keys[
                cls._geometry_key(edge)
            ] = index

        for item in edge_dimensions:

            if not isinstance(
                item,
                (tuple, list),
            ):
                continue

            if len(item) < 2:
                continue

            dimension = item[0]
            edge = item[1]

            metric_value = getattr(
                dimension,
                "metric_value",
                None,
            )

            if metric_value is None:
                metric_value = getattr(
                    dimension,
                    "value",
                    None,
                )

            if not isinstance(
                metric_value,
                (int, float),
            ):
                continue

            key = cls._geometry_key(
                edge
            )

            edge_index = edge_keys.get(
                key
            )

            if edge_index is None:
                continue

            edge_records[
                edge_index
            ].append(
                float(
                    metric_value
                )
            )

        # --------------------------------------------------------------
        # Only retain exactly one measurement per edge.
        # --------------------------------------------------------------

        result = {}

        for edge_index, values in edge_records.items():

            if len(values) != 1:
                continue

            result[
                f"edge_{edge_index + 1}"
            ] = values[0]

        return result

    # ==================================================================
    # SHAPE
    # ==================================================================

    @staticmethod
    def _classify_boundary_shape(
        plot_boundary: Any,
        segments: list[Any],
    ) -> str | None:

        metadata = getattr(
            plot_boundary,
            "metadata",
            {},
        )

        if isinstance(
            metadata,
            dict,
        ):

            explicit_shape = metadata.get(
                "shape"
            )

            if explicit_shape:
                return str(
                    explicit_shape
                )

        count = len(
            segments
        )

        if count == 3:
            return "triangle"

        if count == 4:
            return "quadrilateral"

        if count > 4:
            return "polygon"

        return None

    # ==================================================================
    # DIMENSION RECORD
    # ==================================================================

    @classmethod
    def _dimension_record(
        cls,
        dimension: Any,
    ) -> dict[str, Any]:

        if dimension is None:
            return {}

        return {
            "value": getattr(
                dimension,
                "value",
                None,
            ),
            "metric_value": getattr(
                dimension,
                "metric_value",
                None,
            ),
            "unit": getattr(
                dimension,
                "unit",
                None,
            ),
            "confidence": getattr(
                dimension,
                "confidence",
                None,
            ),
            "line": cls._geometry_repr(
                getattr(
                    dimension,
                    "line",
                    None,
                )
            ),
        }

    # ==================================================================
    # HELPERS
    # ==================================================================

    @staticmethod
    def _first_value(
        obj: Any,
        names: tuple[str, ...],
    ) -> Any:

        for name in names:

            value = getattr(
                obj,
                name,
                None,
            )

            if value is not None:
                return value

        return None

    @classmethod
    def _set_if_missing(
        cls,
        facts: PlanningFacts,
        field_name: str,
        value: Any,
    ) -> None:

        if value is None:
            return

        if field_name in cls.FORBIDDEN_FIELDS:

            raise ValueError(
                "VisionPlanningFactsAdapter attempted "
                "to populate forbidden field: "
                f"{field_name}"
            )

        # --------------------------------------------------------------
        # Field must actually exist on PlanningFacts.
        # --------------------------------------------------------------

        available = {
            field.name
            for field in fields(
                PlanningFacts
            )
        }

        if field_name not in available:

            raise AttributeError(
                "PlanningFacts does not contain "
                f"field '{field_name}'"
            )

        current = getattr(
            facts,
            field_name,
            None,
        )

        # --------------------------------------------------------------
        # Preserve an already supplied authoritative fact.
        #
        # Empty dict/list/string values are considered missing.
        # --------------------------------------------------------------

        if cls._has_value(
            current
        ):
            return

        setattr(
            facts,
            field_name,
            value,
        )

    @staticmethod
    def _has_value(
        value: Any,
    ) -> bool:

        if value is None:
            return False

        if isinstance(
            value,
            str,
        ):
            return bool(
                value.strip()
            )

        if isinstance(
            value,
            (list, tuple, set, dict),
        ):
            return bool(
                value
            )

        return True

    @staticmethod
    def _record_source(
        facts: PlanningFacts,
        field_name: str,
        source: str,
        confidence: float | None = None,
        evidence: Any = None,
    ) -> None:

        facts.fact_sources[
            field_name
        ] = source

        if confidence is not None:

            facts.fact_confidence[
                field_name
            ] = float(
                confidence
            )

        if evidence is not None:

            facts.fact_evidence[
                field_name
            ] = evidence

    @staticmethod
    def _geometry_key(
        geometry: Any,
    ) -> str:

        if geometry is None:
            return ""

        wkt = getattr(
            geometry,
            "wkt",
            None,
        )

        if wkt is not None:
            return str(
                wkt
            )

        return repr(
            geometry
        )

    @staticmethod
    def _geometry_repr(
        geometry: Any,
    ) -> Any:

        if geometry is None:
            return None

        # --------------------------------------------------------------
        # Shapely / LineString etc.
        # --------------------------------------------------------------

        wkt = getattr(
            geometry,
            "wkt",
            None,
        )

        if wkt is not None:
            return wkt

        # --------------------------------------------------------------
        # Vision Polygon / Point style objects.
        # --------------------------------------------------------------

        vertices = getattr(
            geometry,
            "vertices",
            None,
        )

        if vertices is not None:

            result = []

            for point in vertices:

                result.append(
                    {
                        "x": getattr(
                            point,
                            "x",
                            None,
                        ),
                        "y": getattr(
                            point,
                            "y",
                            None,
                        ),
                    }
                )

            return result

        # --------------------------------------------------------------
        # Generic object fallback.
        # --------------------------------------------------------------

        return repr(
            geometry
        )

    # ==================================================================
    # SCHEMA VALIDATION
    # ==================================================================

    @classmethod
    def _validate_schema(
        cls,
    ) -> None:

        available = {
            field.name
            for field in fields(
                PlanningFacts
            )
        }

        missing = (
            cls.VISION_FIELDS
            - available
        )

        if missing:

            raise RuntimeError(
                "PlanningFacts schema is missing "
                "Vision adapter fields: "
                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )