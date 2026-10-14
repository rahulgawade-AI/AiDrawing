"""
OpenAI-assisted building/unit-mix optimization test.

Purpose
-------
1. User supplies carpet-area constraints for 1/2/3 BHK.
2. Python calculates feasible unit combinations.
3. Python generates candidate geometric layouts.
4. OpenAI evaluates the candidates and recommends the best one.
5. Hard geometry constraints remain deterministic.
6. Waste/unusable space is explicitly scored.

This test DOES NOT use AutoCAD for optimization.
AutoCAD/APS should only be used after a valid plan has been selected.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, asdict
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple

from openai import OpenAI


# ============================================================
# CONFIGURATION
# ============================================================

PLOT_AREA_M2 = 745.6
FSI = 2.5
FLOORS = 5

# Example user input.
#
# IMPORTANT:
# These are examples only.
# Replace these values with actual user input later.
#
# 1 BHK < 500 sqft
# 2 BHK < 800 sqft
# 3 BHK < 1100 sqft
#
# We use practical lower bounds as well.
CARPET_REQUIREMENTS = {
    "1BHK": {
        "min_sqft": 400,
        "max_sqft": 500,
    },
    "2BHK": {
        "min_sqft": 650,
        "max_sqft": 800,
    },
    "3BHK": {
        "min_sqft": 900,
        "max_sqft": 1100,
    },
}


SQFT_TO_M2 = 0.092903


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class UnitType:
    name: str
    min_sqft: float
    max_sqft: float

    @property
    def min_m2(self) -> float:
        return self.min_sqft * SQFT_TO_M2

    @property
    def max_m2(self) -> float:
        return self.max_sqft * SQFT_TO_M2


@dataclass
class UnitMix:
    units_1bhk: int
    units_2bhk: int
    units_3bhk: int

    @property
    def total_units(self) -> int:
        return (
            self.units_1bhk
            + self.units_2bhk
            + self.units_3bhk
        )


@dataclass
class CandidatePlan:
    mix: UnitMix
    average_carpet_sqft: float
    total_carpet_area_m2: float
    residential_area_m2: float
    circulation_m2: float
    core_m2: float
    waste_m2: float
    utilization_percent: float
    score: float


# ============================================================
# BASIC BUILDING CALCULATIONS
# ============================================================

def calculate_max_builtup_area() -> float:
    return PLOT_AREA_M2 * FSI


def calculate_footprint() -> float:
    """
    Simplified footprint assumption.

    In the production implementation this must come from:
        plot geometry
        setbacks
        road width
        height rules
        coverage
        fire requirements
        etc.
    """

    max_builtup = calculate_max_builtup_area()

    return max_builtup / FLOORS


def calculate_building_envelope() -> Dict[str, float]:
    footprint = calculate_footprint()

    # Approximate rectangular envelope for this test.
    width = math.sqrt(footprint * 1.15)
    depth = footprint / width

    return {
        "area_m2": footprint,
        "width_m": width,
        "depth_m": depth,
    }


# ============================================================
# UNIT TYPES
# ============================================================

def load_unit_types() -> Dict[str, UnitType]:
    return {
        name: UnitType(
            name=name,
            min_sqft=data["min_sqft"],
            max_sqft=data["max_sqft"],
        )
        for name, data in CARPET_REQUIREMENTS.items()
    }


# ============================================================
# UNIT AREA SELECTION
# ============================================================

def target_unit_area_sqft(unit_type: UnitType) -> float:
    """
    Select a reasonable target area inside the user's range.

    We intentionally do NOT always use the maximum.
    """

    return (unit_type.min_sqft + unit_type.max_sqft) / 2.0


# ============================================================
# UNIT MIX GENERATION
# ============================================================

def estimate_carpet_area_for_mix(
    mix: UnitMix,
    unit_types: Dict[str, UnitType],
) -> float:

    area_sqft = (
        mix.units_1bhk
        * target_unit_area_sqft(unit_types["1BHK"])
    )

    area_sqft += (
        mix.units_2bhk
        * target_unit_area_sqft(unit_types["2BHK"])
    )

    area_sqft += (
        mix.units_3bhk
        * target_unit_area_sqft(unit_types["3BHK"])
    )

    return area_sqft * SQFT_TO_M2


def generate_candidate_mixes(
    residential_area_m2: float,
    unit_types: Dict[str, UnitType],
) -> List[UnitMix]:

    candidates: List[UnitMix] = []

    # Avoid arbitrary hardcoded "21 units".
    #
    # The maximum possible units are derived from
    # the smallest configured unit.
    smallest_unit_m2 = min(
        u.min_m2 for u in unit_types.values()
    )

    theoretical_max_units = int(
        residential_area_m2 / smallest_unit_m2
    )

    # Search combinations.
    for n1 in range(0, theoretical_max_units + 1):
        for n2 in range(0, theoretical_max_units + 1):
            for n3 in range(0, theoretical_max_units + 1):

                total = n1 + n2 + n3

                if total == 0:
                    continue

                mix = UnitMix(
                    units_1bhk=n1,
                    units_2bhk=n2,
                    units_3bhk=n3,
                )

                carpet_area = estimate_carpet_area_for_mix(
                    mix,
                    unit_types,
                )

                # Leave room for common/core/circulation.
                if carpet_area > residential_area_m2:
                    continue

                candidates.append(mix)

    return candidates


# ============================================================
# GEOMETRIC / AREA MODEL
# ============================================================

def evaluate_mix_geometry(
    mix: UnitMix,
    unit_types: Dict[str, UnitType],
    building_area_m2: float,
) -> CandidatePlan:

    carpet_area_m2 = estimate_carpet_area_for_mix(
        mix,
        unit_types,
    )

    # Initial planning allowance.
    #
    # These should eventually come from the actual geometry
    # generated by the layout engine.
    core_m2 = building_area_m2 * 0.08
    circulation_m2 = building_area_m2 * 0.10

    usable_residential_area = (
        building_area_m2
        - core_m2
        - circulation_m2
    )

    waste_m2 = max(
        0.0,
        usable_residential_area - carpet_area_m2,
    )

    if usable_residential_area > 0:
        utilization = (
            carpet_area_m2
            / usable_residential_area
            * 100.0
        )
    else:
        utilization = 0.0

    # Lower is better.
    #
    # Penalize:
    #   - waste
    #   - excessive circulation
    #
    # Reward:
    #   - higher usable carpet area
    #   - more units
    score = (
        waste_m2 * 10
        + circulation_m2 * 2
        - carpet_area_m2
        - mix.total_units * 2
    )

    average_carpet = (
        carpet_area_m2 / mix.total_units / SQFT_TO_M2
    )

    return CandidatePlan(
        mix=mix,
        average_carpet_sqft=average_carpet,
        total_carpet_area_m2=carpet_area_m2,
        residential_area_m2=usable_residential_area,
        circulation_m2=circulation_m2,
        core_m2=core_m2,
        waste_m2=waste_m2,
        utilization_percent=utilization,
        score=score,
    )


# ============================================================
# HARD VALIDATION
# ============================================================

def validate_candidate(
    candidate: CandidatePlan,
    unit_types: Dict[str, UnitType],
) -> Tuple[bool, List[str]]:

    errors: List[str] = []

    mix = candidate.mix

    if mix.total_units <= 0:
        errors.append("No units generated.")

    for name, count in [
        ("1BHK", mix.units_1bhk),
        ("2BHK", mix.units_2bhk),
        ("3BHK", mix.units_3bhk),
    ]:

        if count < 0:
            errors.append(
                f"{name}: negative unit count."
            )

    if candidate.waste_m2 < 0:
        errors.append(
            "Waste area cannot be negative."
        )

    if candidate.utilization_percent > 100.0:
        errors.append(
            "Utilization exceeds 100%."
        )

    return len(errors) == 0, errors


# ============================================================
# OPENAI EVALUATION
# ============================================================

def openai_evaluate_candidates(
    candidates: List[CandidatePlan],
) -> Dict:

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set.\n"
            "Run:\n"
            "export OPENAI_API_KEY='your-key'"
        )

    client = OpenAI(api_key=api_key)

    # Send only the best deterministic candidates.
    #
    # OpenAI should not receive hundreds/thousands of
    # geometrically equivalent candidates.
    candidates = sorted(
        candidates,
        key=lambda c: c.score,
    )[:20]

    candidate_json = []

    for index, candidate in enumerate(candidates):

        candidate_json.append({
            "candidate_id": index,
            "unit_mix": asdict(candidate.mix),
            "total_units": candidate.mix.total_units,
            "average_carpet_sqft": round(
                candidate.average_carpet_sqft,
                2,
            ),
            "total_carpet_area_m2": round(
                candidate.total_carpet_area_m2,
                2,
            ),
            "residential_area_m2": round(
                candidate.residential_area_m2,
                2,
            ),
            "circulation_m2": round(
                candidate.circulation_m2,
                2,
            ),
            "core_m2": round(
                candidate.core_m2,
                2,
            ),
            "waste_m2": round(
                candidate.waste_m2,
                2,
            ),
            "utilization_percent": round(
                candidate.utilization_percent,
                2,
            ),
            "deterministic_score": round(
                candidate.score,
                2,
            ),
        })

    system_prompt = """
You are an architectural planning optimization assistant.

You are NOT the CAD engine.

Your job is to evaluate candidate residential unit mixes.

Important:
- Do not invent measurements.
- Do not change user carpet-area constraints.
- Do not claim a plan is code-compliant unless explicitly verified.
- Prefer efficient layouts with low unusable/waste space.
- Avoid disproportionate room allocation.
- A living/dining room should not become smaller than a master bedroom
  without a strong architectural reason.
- Bathrooms must be located within the unit.
- Kitchen and toilet geometries must not overlap.
- Bedrooms, kitchen, toilets and living spaces must have sensible
  relationships and dimensions.
- Prefer repeated/stacked layouts where appropriate.
- Prefer simple rectangular geometry.
- Minimize unnecessary corridors.
- Minimize unusable residual spaces.

Select the best candidate from the supplied candidates.

Return JSON only.
"""

    user_prompt = f"""
Building information:

Plot area:
{PLOT_AREA_M2} m²

FSI:
{FSI}

Floors:
{FLOORS}

Maximum built-up:
{calculate_max_builtup_area():.2f} m²

Unit carpet constraints:
{json.dumps(CARPET_REQUIREMENTS, indent=2)}

Candidate mixes:

{json.dumps(candidate_json, indent=2)}

Select the best candidate.

Return exactly:

{{
  "selected_candidate_id": 0,
  "reason": "...",
  "design_priorities": [
    "...",
    "...",
    "..."
  ],
  "warnings": [
    "..."
  ]
}}
"""

    response = client.responses.create(
        model="gpt-5",
        instructions=system_prompt,
        input=user_prompt,
    )

    text = response.output_text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:

        print("\nOpenAI returned:\n")
        print(text)

        raise RuntimeError(
            "OpenAI response was not valid JSON."
        )


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("=" * 80)
    print("OPENAI BUILDING / UNIT-MIX OPTIMIZATION TEST")
    print("=" * 80)

    unit_types = load_unit_types()

    max_builtup = calculate_max_builtup_area()

    footprint = calculate_footprint()

    envelope = calculate_building_envelope()

    # For this test, we assume the full footprint is available
    # to residential planning.
    #
    # Production implementation must subtract:
    #   stairs
    #   lift
    #   fire escape
    #   services
    #   shafts
    #   required common areas
    residential_area = footprint

    print()
    print(f"Plot area       : {PLOT_AREA_M2:.2f} m²")
    print(f"FSI             : {FSI}")
    print(f"Maximum builtup : {max_builtup:.2f} m²")
    print(f"Floors          : {FLOORS}")
    print(f"Floor footprint : {footprint:.2f} m²")

    print()
    print("UNIT CARPET CONSTRAINTS")
    print("-" * 80)

    for unit in unit_types.values():

        print(
            f"{unit.name}: "
            f"{unit.min_sqft:.0f}–"
            f"{unit.max_sqft:.0f} sqft "
            f"("
            f"{unit.min_m2:.2f}–"
            f"{unit.max_m2:.2f} m²"
            f")"
        )

    print()
    print("GENERATING UNIT MIXES...")
    print("-" * 80)

    mixes = generate_candidate_mixes(
        residential_area,
        unit_types,
    )

    print(
        f"Feasible mathematical mixes: "
        f"{len(mixes)}"
    )

    # Evaluate every mathematical candidate.
    evaluated: List[CandidatePlan] = []

    for mix in mixes:

        candidate = evaluate_mix_geometry(
            mix,
            unit_types,
            residential_area,
        )

        valid, errors = validate_candidate(
            candidate,
            unit_types,
        )

        if valid:
            evaluated.append(candidate)

    if not evaluated:
        raise RuntimeError(
            "No valid unit mix found."
        )

    # Deterministic pre-ranking.
    evaluated.sort(
        key=lambda c: c.score
    )

    print()
    print("TOP DETERMINISTIC CANDIDATES")
    print("-" * 80)

    for index, candidate in enumerate(
        evaluated[:10]
    ):

        mix = candidate.mix

        print(
            f"{index:02d} | "
            f"1BHK={mix.units_1bhk} "
            f"2BHK={mix.units_2bhk} "
            f"3BHK={mix.units_3bhk} | "
            f"units={mix.total_units} | "
            f"carpet="
            f"{candidate.total_carpet_area_m2:.2f} m² | "
            f"waste="
            f"{candidate.waste_m2:.2f} m² | "
            f"util="
            f"{candidate.utilization_percent:.2f}%"
        )

    print()
    print("ASKING OPENAI TO EVALUATE CANDIDATES...")
    print("-" * 80)

    ai_result = openai_evaluate_candidates(
        evaluated
    )

    print()
    print("OPENAI DECISION")
    print("=" * 80)

    print(
        json.dumps(
            ai_result,
            indent=2,
        )
    )

    selected_id = ai_result.get(
        "selected_candidate_id"
    )

    if selected_id is None:
        raise RuntimeError(
            "OpenAI did not return selected_candidate_id."
        )

    shortlisted = sorted(
        evaluated,
        key=lambda c: c.score,
    )[:20]

    if not (
        isinstance(selected_id, int)
        and 0 <= selected_id < len(shortlisted)
    ):
        raise RuntimeError(
            f"Invalid candidate ID returned by OpenAI: "
            f"{selected_id}"
        )

    selected = shortlisted[selected_id]

    print()
    print("=" * 80)
    print("SELECTED UNIT MIX")
    print("=" * 80)

    print(
        f"1BHK : {selected.mix.units_1bhk}"
    )
    print(
        f"2BHK : {selected.mix.units_2bhk}"
    )
    print(
        f"3BHK : {selected.mix.units_3bhk}"
    )
    print(
        f"TOTAL: {selected.mix.total_units}"
    )

    print()
    print("AREA")
    print("-" * 80)

    print(
        f"Carpet area : "
        f"{selected.total_carpet_area_m2:.2f} m²"
    )

    print(
        f"Residential : "
        f"{selected.residential_area_m2:.2f} m²"
    )

    print(
        f"Circulation : "
        f"{selected.circulation_m2:.2f} m²"
    )

    print(
        f"Core        : "
        f"{selected.core_m2:.2f} m²"
    )

    print(
        f"Waste       : "
        f"{selected.waste_m2:.2f} m²"
    )

    print(
        f"Utilization : "
        f"{selected.utilization_percent:.2f}%"
    )

    # ========================================================
    # SAVE RESULT
    # ========================================================

    output_dir = Path(
        "/tmp/openai_building_optimizer"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = {
        "building": {
            "plot_area_m2": PLOT_AREA_M2,
            "fsi": FSI,
            "floors": FLOORS,
            "maximum_builtup_m2": max_builtup,
            "footprint_m2": footprint,
            "envelope": envelope,
        },
        "carpet_requirements": CARPET_REQUIREMENTS,
        "selected_unit_mix": asdict(
            selected.mix
        ),
        "selected_plan": asdict(
            selected
        ),
        "openai_evaluation": ai_result,
    }

    output_file = (
        output_dir / "optimization_result.json"
    )

    output_file.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("OPTIMIZATION SUCCESSFUL")
    print("=" * 80)

    print(
        f"Result: {output_file}"
    )

    print()
    print(
        "NEXT STEP:"
    )

    print(
        "Generate actual room geometry from the selected "
        "unit mix, validate it deterministically, then "
        "send the validated geometry to AutoCAD APS."
    )


if __name__ == "__main__":
    main()
