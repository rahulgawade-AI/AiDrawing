from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import cv2
import numpy as np

from townplanning.modules.vision.domain.point import Point
from townplanning.modules.vision.domain.polygon import Polygon

try:
    from townplanning.modules.vision.ai.plot_ai_detector import (
        AIPlotCandidate,
        AIPlotDetector,
    )
except Exception:
    AIPlotCandidate = Any
    AIPlotDetector = None


# ---------------------------------------------------------------------------
# Candidate model
# ---------------------------------------------------------------------------

@dataclass
class PlotCandidate:
    points: list[tuple[float, float]]
    source: str

    geometry_score: float = 0.0
    text_score: float = 0.0
    dimension_score: float = 0.0
    ai_score: float = 0.0
    border_penalty: float = 0.0

    area_score: float = 0.0
    shape_score: float = 0.0
    compactness_score: float = 0.0

    score: float = 0.0

    evidence: dict[str, Any] = field(default_factory=dict)

    def calculate_score(self) -> float:
        """
        Deterministic weighted evidence score.

        AI is supporting evidence only. A missing AI provider therefore does
        not prevent CV/OCR/dimension based detection.
        """

        raw = (
            0.25 * self.geometry_score
            + 0.20 * self.text_score
            + 0.25 * self.dimension_score
            + 0.15 * self.ai_score
            + 0.05 * self.area_score
            + 0.05 * self.shape_score
            + 0.05 * self.compactness_score
        )

        raw -= self.border_penalty

        self.score = float(max(0.0, min(1.0, raw)))
        return self.score


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class PlotDetector:
    """
    Hybrid plot-boundary detector.

    Detection sources:

        1. OpenCV contours / edges
        2. adaptive threshold contours
        3. color-region contours
        4. existing geometry where available
        5. OCR evidence
        6. dimension-line evidence
        7. optional Ollama/OpenAI vision

    Important:

        AI never becomes authoritative geometry.

        AI -> candidate
        CV/OCR/dimensions -> validation/refinement
        final polygon -> deterministic result
    """

    MIN_AREA_RATIO = 0.015
    MAX_AREA_RATIO = 0.90

    MIN_POINTS = 3
    MAX_POINTS = 12

    BORDER_MARGIN = 0.035

    # Candidate scoring.
    TEXT_RADIUS = 260.0
    DIMENSION_DISTANCE_TOLERANCE = 45.0

    def __init__(
        self,
        ai_detector: Optional[Any] = None,
        enable_ai: bool = True,
    ) -> None:
        self.enable_ai = enable_ai

        if ai_detector is not None:
            self.ai_detector = ai_detector
        elif enable_ai and AIPlotDetector is not None:
            try:
                self.ai_detector = AIPlotDetector()
            except Exception as exc:
                print(f"[PLOT AI] initialization failed: {exc}")
                self.ai_detector = None
        else:
            self.ai_detector = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        drawing: Any = None,
        image: Any = None,
        image_path: str | Path | None = None,
        texts: Optional[Iterable[Any]] = None,
        dimensions: Optional[Iterable[Any]] = None,
    ) -> Optional[Polygon]:
        """
        Detect plot polygon.

        Backward compatible with the old call:

            detect(drawing, image)

        New preferred call:

            New preferred call:
        
        detect(
            drawing=drawing,
            image=image,
            image_path=image_path,
            texts=texts,
            dimensions=dimensions,
        )
        """
        if image_path is None and isinstance(
            image,
            (str, Path),
        ):
            image_path = image

        image_np = self._normalise_image(image=image, image_path=image_path)

        if image_np is None:
            print("[PLOT] no usable image")
            return None

        height, width = image_np.shape[:2]

        if width < 20 or height < 20:
            print("[PLOT] image too small")
            return None

        candidates: list[PlotCandidate] = []

        # --------------------------------------------------------------
        # 1. Existing geometry
        # --------------------------------------------------------------

        candidates.extend(
            self._geometry_candidates(
                drawing=drawing,
                width=width,
                height=height,
            )
        )

        # --------------------------------------------------------------
        # 2. OpenCV image candidates
        # --------------------------------------------------------------

        candidates.extend(
            self._opencv_candidates(
                image=image_np,
                width=width,
                height=height,
            )
        )

        # --------------------------------------------------------------
        # 3. Optional AI candidate
        # --------------------------------------------------------------

        ai_candidates = self._ai_candidates(
            image=image_np,
            image_path=image_path,
            width=width,
            height=height,
        )

        candidates.extend(ai_candidates)

        if not candidates:
            print("[PLOT] no candidates generated")
            return None

        # --------------------------------------------------------------
        # 4. Clean/refine candidates
        # --------------------------------------------------------------

        refined: list[PlotCandidate] = []

        for candidate in candidates:
            cleaned = self._refine_candidate(
                candidate,
                width=width,
                height=height,
            )

            if cleaned is None:
                continue

            refined.append(cleaned)

        if not refined:
            print("[PLOT] no valid candidates after refinement")
            return None

        # --------------------------------------------------------------
        # 5. OCR + dimension evidence
        # --------------------------------------------------------------

        for candidate in refined:
            self._score_text_evidence(
                candidate=candidate,
                texts=texts,
            )

            self._score_dimension_evidence(
                candidate=candidate,
                dimensions=dimensions,
            )

            self._score_visual_geometry(
                candidate=candidate,
                width=width,
                height=height,
            )

            self._score_border(
                candidate=candidate,
                width=width,
                height=height,
            )

            candidate.calculate_score()

        # --------------------------------------------------------------
        # 6. Deduplicate
        # --------------------------------------------------------------

        refined = self._deduplicate(refined)

        # --------------------------------------------------------------
        # 7. Rank
        # --------------------------------------------------------------

        refined.sort(
            key=lambda candidate: candidate.score,
            reverse=True,
        )

        self._print_ranking(refined)

        selected = refined[0]

        if selected.score < 0.20:
            print(
                "[PLOT] selected candidate has low confidence:",
                round(selected.score, 3),
            )

        print(
            "[PLOT] selected:",
            selected.source,
            "score=",
            round(selected.score, 3),
            "points=",
            len(selected.points),
        )

        return self._to_domain_polygon(selected.points)

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------

    def _normalise_image(
    self,
    image: Any,
    image_path: str | Path | None,
    ) -> Optional[np.ndarray]:

    # --------------------------------------------------------------

    # Case 1: OpenCV / NumPy image
    # --------------------------------------------------------------
            if isinstance(image, np.ndarray):

                if image.ndim == 2:
                    return cv2.cvtColor(
                        image,
                        cv2.COLOR_GRAY2BGR,
                    )

                if image.ndim == 3:
                    return image.copy()

                return None

    # --------------------------------------------------------------
    # Case 2: Path passed as the old second positional argument
    #
    # Existing test:
    #
    #   detect(drawing, image)
    #
    # where image is actually a Path.
    # --------------------------------------------------------------
            if isinstance(image, (str, Path)):

                if image_path is None:
                    image_path = image

                try:
                    loaded = cv2.imread(
                        str(image),
                        cv2.IMREAD_COLOR,
                    )

                    if loaded is not None:
                        return loaded

                except Exception as exc:
                    print(
                        f"[PLOT] image load failed: {exc}"
                    )

    # --------------------------------------------------------------
    # Case 3: Generic array-like object
    # --------------------------------------------------------------
            if image is not None:

                try:
                    array = np.asarray(image)

                    if array.ndim == 2:
                        return cv2.cvtColor(
                            array,
                            cv2.COLOR_GRAY2BGR,
                        )

                    if array.ndim == 3:
                        return array.copy()

                except Exception:
                    pass

    # --------------------------------------------------------------
    # Case 4: Explicit image_path
    # --------------------------------------------------------------
            if image_path is not None:

                try:
                    loaded = cv2.imread(
                        str(image_path),
                        cv2.IMREAD_COLOR,
                    )

                    if loaded is not None:
                        return loaded

                except Exception as exc:
                    print(
                        f"[PLOT] image load failed: {exc}"
                    )

            return None

    # ------------------------------------------------------------------
    # Existing geometry
    # ------------------------------------------------------------------

    def _geometry_candidates(
        self,
        drawing: Any,
        width: int,
        height: int,
    ) -> list[PlotCandidate]:

        candidates: list[PlotCandidate] = []

        if drawing is None:
            return candidates

        objects: list[Any] = [drawing]

        for attribute in (
            "geometry",
            "page",
            "pages",
            "polylines",
            "boundaries",
            "regions",
        ):
            value = getattr(drawing, attribute, None)

            if value is None:
                continue

            if isinstance(value, (list, tuple)):
                objects.extend(value)
            else:
                objects.append(value)

        seen: set[int] = set()

        for obj in objects:
            object_id = id(obj)

            if object_id in seen:
                continue

            seen.add(object_id)

            for attribute in (
                "boundaries",
                "polylines",
                "polygons",
                "regions",
            ):
                items = getattr(obj, attribute, None)

                if items is None:
                    continue

                if not isinstance(items, (list, tuple)):
                    items = [items]

                for item in items:
                    points = self._extract_points(item)

                    if len(points) < 3:
                        continue

                    candidates.append(
                        PlotCandidate(
                            points=points,
                            source="geometry",
                            geometry_score=0.90,
                            evidence={
                                "geometry_object": type(item).__name__,
                            },
                        )
                    )

        return candidates

    def _extract_points(self, obj: Any) -> list[tuple[float, float]]:
        if obj is None:
            return []

        # Direct vertices.
        vertices = getattr(obj, "vertices", None)

        if vertices is not None:
            result = []

            for point in vertices:
                xy = self._point_xy(point)

                if xy is not None:
                    result.append(xy)

            return result

        # Boundary segments.
        segments = getattr(obj, "segments", None)

        if segments is not None:
            result = []

            for segment in segments:
                start = self._point_xy(
                    getattr(segment, "start", None)
                )
                end = self._point_xy(
                    getattr(segment, "end", None)
                )

                if start is not None:
                    result.append(start)

                if end is not None:
                    result.append(end)

            return self._unique_points(result)

        # Generic iterable.
        if isinstance(obj, (list, tuple)):
            result = []

            for point in obj:
                xy = self._point_xy(point)

                if xy is not None:
                    result.append(xy)

            return self._unique_points(result)

        return []

    def _point_xy(self, point: Any) -> Optional[tuple[float, float]]:
        if point is None:
            return None

        x = getattr(point, "x", None)
        y = getattr(point, "y", None)

        if x is not None and y is not None:
            try:
                return float(x), float(y)
            except Exception:
                return None

        if isinstance(point, (list, tuple)) and len(point) >= 2:
            try:
                return float(point[0]), float(point[1])
            except Exception:
                return None

        return None

    # ------------------------------------------------------------------
    # OpenCV candidate generation
    # ------------------------------------------------------------------

    def _opencv_candidates(
        self,
        image: np.ndarray,
        width: int,
        height: int,
    ) -> list[PlotCandidate]:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        candidates: list[PlotCandidate] = []

        # --------------------------------------------------------------
        # A. Canny edges
        # --------------------------------------------------------------

        edges = cv2.Canny(
            gray,
            threshold1=40,
            threshold2=130,
        )

        edges = cv2.dilate(
            edges,
            np.ones((3, 3), np.uint8),
            iterations=1,
        )

        candidates.extend(
            self._contour_candidates(
                mask=edges,
                source="opencv_edges",
                width=width,
                height=height,
            )
        )

        # --------------------------------------------------------------
        # B. Adaptive threshold
        # --------------------------------------------------------------

        adaptive = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            7,
        )

        adaptive = cv2.morphologyEx(
            adaptive,
            cv2.MORPH_CLOSE,
            np.ones((5, 5), np.uint8),
            iterations=2,
        )

        candidates.extend(
            self._contour_candidates(
                mask=adaptive,
                source="opencv_adaptive",
                width=width,
                height=height,
            )
        )

        # --------------------------------------------------------------
        # C. Saturated/color region
        # --------------------------------------------------------------

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV,
        )

        saturation = hsv[:, :, 1]

        color_mask = cv2.inRange(
            saturation,
            35,
            255,
        )

        color_mask = cv2.morphologyEx(
            color_mask,
            cv2.MORPH_CLOSE,
            np.ones((9, 9), np.uint8),
            iterations=2,
        )

        candidates.extend(
            self._contour_candidates(
                mask=color_mask,
                source="opencv_color_region",
                width=width,
                height=height,
            )
        )

        # --------------------------------------------------------------
        # D. Green-region detector
        # --------------------------------------------------------------

        # Useful for the current technical sample, but intentionally broad
        # enough for colored site plans.
        green_mask = cv2.inRange(
            hsv,
            np.array([25, 25, 20], dtype=np.uint8),
            np.array([100, 255, 255], dtype=np.uint8),
        )

        green_mask = cv2.morphologyEx(
            green_mask,
            cv2.MORPH_CLOSE,
            np.ones((11, 11), np.uint8),
            iterations=2,
        )

        candidates.extend(
            self._contour_candidates(
                mask=green_mask,
                source="opencv_green_region",
                width=width,
                height=height,
            )
        )

        return candidates

    def _contour_candidates(
        self,
        mask: np.ndarray,
        source: str,
        width: int,
        height: int,
    ) -> list[PlotCandidate]:

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        image_area = float(width * height)

        candidates: list[PlotCandidate] = []

        # Largest useful contours first.
        contours = sorted(
            contours,
            key=cv2.contourArea,
            reverse=True,
        )

        for contour in contours[:80]:

            area = float(cv2.contourArea(contour))

            ratio = area / image_area

            if ratio < self.MIN_AREA_RATIO:
                continue

            if ratio > self.MAX_AREA_RATIO:
                continue

            perimeter = cv2.arcLength(
                contour,
                True,
            )

            if perimeter <= 0:
                continue

            # Multiple epsilon values prevent one contour shape from being
            # permanently over-simplified.
            for epsilon_ratio in (
                0.005,
                0.010,
                0.015,
                0.020,
                0.030,
            ):
                approx = cv2.approxPolyDP(
                    contour,
                    epsilon_ratio * perimeter,
                    True,
                )

                points = [
                    (
                        float(point[0][0]),
                        float(point[0][1]),
                    )
                    for point in approx
                ]

                points = self._refine_points(
                    points,
                    width,
                    height,
                )

                if not self._valid_polygon(points):
                    continue

                candidates.append(
                    PlotCandidate(
                        points=points,
                        source=source,
                        geometry_score=self._initial_geometry_score(
                            points,
                            width,
                            height,
                        ),
                        area_score=self._area_score(
                            points,
                            width,
                            height,
                        ),
                        shape_score=self._shape_score(points),
                        compactness_score=self._compactness_score(points),
                        evidence={
                            "contour_area_ratio": ratio,
                            "epsilon_ratio": epsilon_ratio,
                        },
                    )
                )

        return candidates

    # ------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------

    def _ai_candidates(
        self,
        image: np.ndarray,
        image_path: str | Path | None,
        width: int,
        height: int,
    ) -> list[PlotCandidate]:

        if self.ai_detector is None:
            return []

        try:
            result = self._run_ai_detector(
                image=image,
                image_path=image_path,
            )

            if result is None:
                return []

            ai_results = result

            if not isinstance(ai_results, (list, tuple)):
                ai_results = [ai_results]

            candidates: list[PlotCandidate] = []

            for item in ai_results:
                points = self._extract_ai_points(
                    item,
                    width,
                    height,
                )

                if len(points) < 3:
                    continue

                confidence = self._extract_ai_confidence(
                    item
                )

                candidates.append(
                    PlotCandidate(
                        points=points,
                        source="ai_vision",
                        ai_score=confidence,
                        geometry_score=0.65,
                        evidence={
                            "ai_confidence": confidence,
                        },
                    )
                )

            return candidates

        except Exception as exc:
            print(
                f"[PLOT AI] provider failed: {exc}"
            )
            return []

    def _run_ai_detector(
        self,
        image: np.ndarray,
        image_path: str | Path | None,
    ) -> Any:

        detector = self.ai_detector

        # Preferred API.
        if hasattr(detector, "detect"):
            try:
                return detector.detect(
                    image=image,
                    image_path=image_path,
                )
            except TypeError:
                pass

            try:
                return detector.detect(image)
            except TypeError:
                pass

            if image_path is not None:
                return detector.detect(image_path)

        return None

    def _extract_ai_points(
        self,
        result: Any,
        width: int,
        height: int,
    ) -> list[tuple[float, float]]:

        points = getattr(
            result,
            "points",
            None,
        )

        if points is None and isinstance(result, dict):
            points = result.get("points")

        if points is None:
            polygon = getattr(
                result,
                "polygon",
                None,
            )

            if polygon is None and isinstance(result, dict):
                polygon = result.get("polygon")

            points = polygon

        if points is None:
            return []

        output = []

        for point in points:
            if isinstance(point, dict):
                x = point.get("x")
                y = point.get("y")
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                x = point[0]
                y = point[1]
            else:
                x = getattr(point, "x", None)
                y = getattr(point, "y", None)

            if x is None or y is None:
                continue

            try:
                x = float(x)
                y = float(y)
            except Exception:
                continue

            # AI prompt uses normalized 0..1000 coordinates.
            if 0.0 <= x <= 1000.0 and 0.0 <= y <= 1000.0:
                x = x / 1000.0 * width
                y = y / 1000.0 * height

            output.append((x, y))

        return output

    def _extract_ai_confidence(
        self,
        result: Any,
    ) -> float:

        confidence = getattr(
            result,
            "confidence",
            None,
        )

        if confidence is None and isinstance(result, dict):
            confidence = result.get("confidence")

        try:
            return max(
                0.0,
                min(1.0, float(confidence)),
            )
        except Exception:
            return 0.70

    # ------------------------------------------------------------------
    # Candidate refinement
    # ------------------------------------------------------------------

    def _refine_candidate(
        self,
        candidate: PlotCandidate,
        width: int,
        height: int,
    ) -> Optional[PlotCandidate]:

        points = self._refine_points(
            candidate.points,
            width,
            height,
        )

        if not self._valid_polygon(points):
            return None

        candidate.points = points

        candidate.area_score = self._area_score(
            points,
            width,
            height,
        )

        candidate.shape_score = self._shape_score(
            points
        )

        candidate.compactness_score = self._compactness_score(
            points
        )

        return candidate

    def _refine_points(
        self,
        points: list[tuple[float, float]],
        width: int,
        height: int,
    ) -> list[tuple[float, float]]:

        points = self._unique_points(points)

        if len(points) < 3:
            return []

        points = self._remove_border_points(
            points,
            width,
            height,
        )

        if len(points) < 3:
            return []

        # Convert to OpenCV contour and simplify again.
        contour = np.asarray(
            points,
            dtype=np.float32,
        ).reshape((-1, 1, 2))

        perimeter = cv2.arcLength(
            contour,
            True,
        )

        if perimeter > 0:
            # Start gently. This removes annotation noise without
            # aggressively destroying genuine irregular corners.
            approx = cv2.approxPolyDP(
                contour,
                max(2.0, perimeter * 0.008),
                True,
            )

            points = [
                (
                    float(p[0][0]),
                    float(p[0][1]),
                )
                for p in approx
            ]

        # Merge nearly-collinear points.
        points = self._remove_collinear_points(
            points,
            tolerance_degrees=8.0,
        )

        # If simplification produced too many points, progressively
        # increase tolerance.
        if len(points) > self.MAX_POINTS:

            contour = np.asarray(
                points,
                dtype=np.float32,
            ).reshape((-1, 1, 2))

            perimeter = cv2.arcLength(
                contour,
                True,
            )

            for epsilon_ratio in (
                0.015,
                0.020,
                0.030,
                0.040,
            ):
                approx = cv2.approxPolyDP(
                    contour,
                    perimeter * epsilon_ratio,
                    True,
                )

                simplified = [
                    (
                        float(p[0][0]),
                        float(p[0][1]),
                    )
                    for p in approx
                ]

                simplified = self._remove_collinear_points(
                    simplified,
                    tolerance_degrees=10.0,
                )

                if (
                    self.MIN_POINTS
                    <= len(simplified)
                    <= self.MAX_POINTS
                ):
                    points = simplified
                    break

        return self._unique_points(points)

    def _remove_collinear_points(
        self,
        points: list[tuple[float, float]],
        tolerance_degrees: float,
    ) -> list[tuple[float, float]]:

        if len(points) <= 3:
            return points

        changed = True

        while changed and len(points) > 3:
            changed = False

            result = []

            n = len(points)

            for i in range(n):
                previous = np.asarray(
                    points[(i - 1) % n],
                    dtype=float,
                )

                current = np.asarray(
                    points[i],
                    dtype=float,
                )

                following = np.asarray(
                    points[(i + 1) % n],
                    dtype=float,
                )

                v1 = previous - current
                v2 = following - current

                norm1 = np.linalg.norm(v1)
                norm2 = np.linalg.norm(v2)

                if norm1 < 1e-6 or norm2 < 1e-6:
                    changed = True
                    continue

                cosine = np.dot(v1, v2) / (
                    norm1 * norm2
                )

                cosine = float(
                    max(-1.0, min(1.0, cosine))
                )

                angle = np.degrees(
                    np.arccos(cosine)
                )

                # A point around 180 degrees is effectively straight.
                deviation = abs(180.0 - angle)

                if deviation <= tolerance_degrees:
                    changed = True
                    continue

                result.append(
                    tuple(current)
                )

            points = result

        return points

    # ------------------------------------------------------------------
    # OCR scoring
    # ------------------------------------------------------------------

    def _score_text_evidence(
        self,
        candidate: PlotCandidate,
        texts: Optional[Iterable[Any]],
    ) -> None:

        if texts is None:
            candidate.text_score = 0.0
            return

        candidate_polygon = self._shapely_polygon(
            candidate.points
        )

        if candidate_polygon is None:
            candidate.text_score = 0.0
            return

        score = 0.0
        evidence = []

        for text in texts:
            value = getattr(
                text,
                "text",
                None,
            )

            if value is None and isinstance(text, dict):
                value = text.get("text")

            if not value:
                continue

            text_upper = str(value).upper()

            box = getattr(
                text,
                "bounding_box",
                None,
            )

            if box is None and isinstance(text, dict):
                box = text.get("bounding_box")

            center = self._bounding_box_center(box)

            if center is None:
                continue

            inside = candidate_polygon.covers(
                self._shapely_point(center)
            )

            if not inside:
                continue

            # Strong plot-specific text.
            if (
                "PLOT" in text_upper
                or "S.NO" in text_upper
                or "SURVEY" in text_upper
                or "SQ.M" in text_upper
                or "SQ.M." in text_upper
            ):
                score += 0.30
                evidence.append(
                    str(value)
                )

            elif (
                "AREA" in text_upper
                or "CTS" in text_upper
            ):
                score += 0.15
                evidence.append(
                    str(value)
                )

        candidate.text_score = min(
            1.0,
            score,
        )

        candidate.evidence[
            "text_matches"
        ] = evidence

    # ------------------------------------------------------------------
    # Dimension scoring
    # ------------------------------------------------------------------

    def _score_dimension_evidence(
        self,
        candidate: PlotCandidate,
        dimensions: Optional[Iterable[Any]],
    ) -> None:

        if dimensions is None:
            candidate.dimension_score = 0.0
            return

        candidate_edges = self._polygon_edges(
            candidate.points
        )

        if not candidate_edges:
            candidate.dimension_score = 0.0
            return

        matched = 0
        total = 0

        evidence = []

        for dimension in dimensions:

            line = getattr(
                dimension,
                "line",
                None,
            )

            if line is None and isinstance(
                dimension,
                dict,
            ):
                line = dimension.get("line")

            if line is None:
                continue

            start = self._point_xy(
                getattr(line, "start", None)
            )

            end = self._point_xy(
                getattr(line, "end", None)
            )

            if start is None or end is None:
                if isinstance(line, dict):
                    start = self._point_xy(
                        line.get("start")
                    )
                    end = self._point_xy(
                        line.get("end")
                    )

            if start is None or end is None:
                continue

            total += 1

            distance = self._distance_line_to_polygon(
                start,
                end,
                candidate_edges,
            )

            if (
                distance
                <= self.DIMENSION_DISTANCE_TOLERANCE
            ):
                matched += 1

                value = getattr(
                    dimension,
                    "value",
                    None,
                )

                if value is None and isinstance(
                    dimension,
                    dict,
                ):
                    value = dimension.get("value")

                evidence.append(
                    {
                        "value": value,
                        "distance": round(
                            float(distance),
                            2,
                        ),
                    }
                )

        if total == 0:
            candidate.dimension_score = 0.0
        else:
            candidate.dimension_score = min(
                1.0,
                matched / max(1, total),
            )

        candidate.evidence[
            "dimension_matches"
        ] = evidence

    # ------------------------------------------------------------------
    # Geometry scoring
    # ------------------------------------------------------------------

    def _score_visual_geometry(
        self,
        candidate: PlotCandidate,
        width: int,
        height: int,
    ) -> None:

        candidate.geometry_score = max(
            candidate.geometry_score,
            self._initial_geometry_score(
                candidate.points,
                width,
                height,
            ),
        )

    def _initial_geometry_score(
        self,
        points: list[tuple[float, float]],
        width: int,
        height: int,
    ) -> float:

        if len(points) < 3:
            return 0.0

        area = self._polygon_area(
            points
        )

        image_area = width * height

        ratio = area / image_area

        if (
            self.MIN_AREA_RATIO
            <= ratio
            <= self.MAX_AREA_RATIO
        ):
            area_component = 1.0
        else:
            area_component = 0.2

        # Prefer actual polygon-like geometry.
        if 3 <= len(points) <= 12:
            vertex_component = 1.0
        else:
            vertex_component = 0.2

        return (
            0.70 * area_component
            + 0.30 * vertex_component
        )

    # ------------------------------------------------------------------
    # Shape / area / compactness
    # ------------------------------------------------------------------

    def _area_score(
        self,
        points: list[tuple[float, float]],
        width: int,
        height: int,
    ) -> float:

        ratio = (
            self._polygon_area(points)
            / float(width * height)
        )

        if 0.03 <= ratio <= 0.65:
            return 1.0

        if 0.015 <= ratio <= 0.85:
            return 0.7

        return 0.25

    def _shape_score(
        self,
        points: list[tuple[float, float]],
    ) -> float:

        if len(points) < 3:
            return 0.0

        # Real land parcels commonly have a small number of meaningful
        # corners. Penalize extreme fragmentation.
        if len(points) in (4, 5, 6):
            return 1.0

        if len(points) in (3, 7, 8):
            return 0.85

        if len(points) in (9, 10):
            return 0.65

        return 0.45

    def _compactness_score(
        self,
        points: list[tuple[float, float]],
    ) -> float:

        area = self._polygon_area(
            points
        )

        perimeter = self._polygon_perimeter(
            points
        )

        if perimeter <= 0:
            return 0.0

        compactness = (
            4.0
            * np.pi
            * area
            / (perimeter * perimeter)
        )

        return float(
            max(
                0.0,
                min(1.0, compactness * 1.5),
            )
        )

    # ------------------------------------------------------------------
    # Border rejection
    # ------------------------------------------------------------------

    def _score_border(
        self,
        candidate: PlotCandidate,
        width: int,
        height: int,
    ) -> None:

        margin_x = width * self.BORDER_MARGIN
        margin_y = height * self.BORDER_MARGIN

        near_border = 0

        for x, y in candidate.points:
            if (
                x <= margin_x
                or x >= width - margin_x
                or y <= margin_y
                or y >= height - margin_y
            ):
                near_border += 1

        ratio = near_border / max(
            1,
            len(candidate.points),
        )

        # Strong rejection for page/frame candidates.
        if ratio >= 0.50:
            candidate.border_penalty = 0.75

        elif ratio >= 0.25:
            candidate.border_penalty = 0.35

        else:
            candidate.border_penalty = 0.0

    def _remove_border_points(
        self,
        points: list[tuple[float, float]],
        width: int,
        height: int,
    ) -> list[tuple[float, float]]:

        # Do not delete individual plot vertices merely because a legitimate
        # plot touches an image edge. Border rejection is handled by scoring.
        return points

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _deduplicate(
        self,
        candidates: list[PlotCandidate],
    ) -> list[PlotCandidate]:

        result: list[PlotCandidate] = []

        for candidate in candidates:

            duplicate = False

            for existing in result:

                if self._polygon_similarity(
                    candidate.points,
                    existing.points,
                ) >= 0.92:

                    duplicate = True

                    if candidate.score > existing.score:
                        existing.points = candidate.points
                        existing.source = (
                            existing.source
                            + "+"
                            + candidate.source
                        )

                        existing.score = candidate.score
                        existing.geometry_score = max(
                            existing.geometry_score,
                            candidate.geometry_score,
                        )
                        existing.text_score = max(
                            existing.text_score,
                            candidate.text_score,
                        )
                        existing.dimension_score = max(
                            existing.dimension_score,
                            candidate.dimension_score,
                        )
                        existing.ai_score = max(
                            existing.ai_score,
                            candidate.ai_score,
                        )

                    break

            if not duplicate:
                result.append(candidate)

        return result

    def _polygon_similarity(
        self,
        a: list[tuple[float, float]],
        b: list[tuple[float, float]],
    ) -> float:

        if len(a) < 3 or len(b) < 3:
            return 0.0

        area_a = self._polygon_area(a)
        area_b = self._polygon_area(b)

        if area_a <= 0 or area_b <= 0:
            return 0.0

        ratio = min(area_a, area_b) / max(
            area_a,
            area_b,
        )

        centroid_a = self._centroid(a)
        centroid_b = self._centroid(b)

        diagonal = max(
            1.0,
            np.hypot(
                max(
                    p[0] for p in a + b
                )
                - min(
                    p[0] for p in a + b
                ),
                max(
                    p[1] for p in a + b
                )
                - min(
                    p[1] for p in a + b
                ),
            ),
        )

        centroid_distance = np.hypot(
            centroid_a[0] - centroid_b[0],
            centroid_a[1] - centroid_b[1],
        )

        location_score = max(
            0.0,
            1.0 - centroid_distance / diagonal,
        )

        return (
            0.70 * ratio
            + 0.30 * location_score
        )

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _valid_polygon(
        self,
        points: list[tuple[float, float]],
    ) -> bool:

        if not (
            self.MIN_POINTS
            <= len(points)
            <= self.MAX_POINTS
        ):
            return False

        area = self._polygon_area(points)

        return area > 10.0

    def _polygon_area(
        self,
        points: list[tuple[float, float]],
    ) -> float:

        if len(points) < 3:
            return 0.0

        pts = np.asarray(
            points,
            dtype=float,
        )

        x = pts[:, 0]
        y = pts[:, 1]

        return float(
            abs(
                np.dot(x, np.roll(y, -1))
                - np.dot(y, np.roll(x, -1))
            )
            * 0.5
        )

    def _polygon_perimeter(
        self,
        points: list[tuple[float, float]],
    ) -> float:

        if len(points) < 2:
            return 0.0

        total = 0.0

        for i in range(len(points)):
            a = points[i]
            b = points[(i + 1) % len(points)]

            total += float(
                np.hypot(
                    a[0] - b[0],
                    a[1] - b[1],
                )
            )

        return total

    def _centroid(
        self,
        points: list[tuple[float, float]],
    ) -> tuple[float, float]:

        pts = np.asarray(
            points,
            dtype=float,
        )

        return (
            float(np.mean(pts[:, 0])),
            float(np.mean(pts[:, 1])),
        )

    def _unique_points(
        self,
        points: list[tuple[float, float]],
        tolerance: float = 1.0,
    ) -> list[tuple[float, float]]:

        result = []

        for point in points:
            if not result:
                result.append(point)
                continue

            if all(
                np.hypot(
                    point[0] - other[0],
                    point[1] - other[1],
                )
                > tolerance
                for other in result
            ):
                result.append(point)

        if len(result) > 1:
            if (
                np.hypot(
                    result[0][0] - result[-1][0],
                    result[0][1] - result[-1][1],
                )
                <= tolerance
            ):
                result.pop()

        return result

    # ------------------------------------------------------------------
    # Dimension geometry helpers
    # ------------------------------------------------------------------

    def _polygon_edges(
        self,
        points: list[tuple[float, float]],
    ) -> list[
        tuple[
            tuple[float, float],
            tuple[float, float],
        ]
    ]:

        return [
            (
                points[i],
                points[(i + 1) % len(points)],
            )
            for i in range(len(points))
        ]

    def _distance_line_to_polygon(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        edges: list[Any],
    ) -> float:

        best = float("inf")

        for edge_start, edge_end in edges:

            distance = self._segment_distance(
                start,
                end,
                edge_start,
                edge_end,
            )

            best = min(
                best,
                distance,
            )

        return best

    def _segment_distance(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
        d: tuple[float, float],
    ) -> float:

        # Sampled segment-to-segment distance. Robust enough for the
        # dimension-evidence stage and avoids requiring a particular
        # geometry library API.

        distances = [
            self._point_to_segment_distance(a, c, d),
            self._point_to_segment_distance(b, c, d),
            self._point_to_segment_distance(c, a, b),
            self._point_to_segment_distance(d, a, b),
        ]

        return min(distances)

    def _point_to_segment_distance(
        self,
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:

        p = np.asarray(point, dtype=float)
        a = np.asarray(start, dtype=float)
        b = np.asarray(end, dtype=float)

        vector = b - a
        length_sq = float(
            np.dot(vector, vector)
        )

        if length_sq <= 1e-12:
            return float(
                np.linalg.norm(p - a)
            )

        t = float(
            np.dot(p - a, vector)
            / length_sq
        )

        t = max(
            0.0,
            min(1.0, t),
        )

        projection = a + t * vector

        return float(
            np.linalg.norm(p - projection)
        )

    # ------------------------------------------------------------------
    # OCR helpers
    # ------------------------------------------------------------------

    def _bounding_box_center(
        self,
        box: Any,
    ) -> Optional[tuple[float, float]]:

        if box is None:
            return None

        min_x = getattr(
            box,
            "min_x",
            None,
        )
        min_y = getattr(
            box,
            "min_y",
            None,
        )
        max_x = getattr(
            box,
            "max_x",
            None,
        )
        max_y = getattr(
            box,
            "max_y",
            None,
        )

        if None not in (
            min_x,
            min_y,
            max_x,
            max_y,
        ):
            return (
                (float(min_x) + float(max_x)) / 2.0,
                (float(min_y) + float(max_y)) / 2.0,
            )

        if isinstance(box, dict):
            try:
                return (
                    (
                        float(box["min_x"])
                        + float(box["max_x"])
                    )
                    / 2.0,
                    (
                        float(box["min_y"])
                        + float(box["max_y"])
                    )
                    / 2.0,
                )
            except Exception:
                return None

        return None

    # ------------------------------------------------------------------
    # Optional shapely support
    # ------------------------------------------------------------------

    def _shapely_polygon(
        self,
        points: list[tuple[float, float]],
    ) -> Any:

        try:
            from shapely.geometry import Polygon as ShapelyPolygon

            polygon = ShapelyPolygon(points)

            if not polygon.is_valid:
                polygon = polygon.buffer(0)

            return polygon

        except Exception:
            return None

    def _shapely_point(
        self,
        point: tuple[float, float],
    ) -> Any:

        from shapely.geometry import Point as ShapelyPoint

        return ShapelyPoint(
            float(point[0]),
            float(point[1]),
        )

    # ------------------------------------------------------------------
    # Domain conversion
    # ------------------------------------------------------------------

    def _to_domain_polygon(
        self,
        points: list[tuple[float, float]],
    ) -> Polygon:

        return Polygon(
            vertices=[
                Point(
                    x=float(x),
                    y=float(y),
                )
                for x, y in points
            ]
        )

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _print_ranking(
        self,
        candidates: list[PlotCandidate],
    ) -> None:

        print()
        print("=" * 100)
        print("PLOT CANDIDATE RANKING")
        print("=" * 100)

        for index, candidate in enumerate(
            candidates[:15],
            start=1,
        ):

            print(
                f"{index:02d}. "
                f"source={candidate.source} "
                f"score={candidate.score:.3f} "
                f"geometry={candidate.geometry_score:.3f} "
                f"text={candidate.text_score:.3f} "
                f"dimension={candidate.dimension_score:.3f} "
                f"ai={candidate.ai_score:.3f} "
                f"area={candidate.area_score:.3f} "
                f"shape={candidate.shape_score:.3f} "
                f"compactness={candidate.compactness_score:.3f} "
                f"border_penalty={candidate.border_penalty:.3f} "
                f"points={len(candidate.points)}"
            )

        print()