# drawing

Drawing stage after deterministic UDCPR resolution.

Flow:

PlanningFacts + deterministic resolver
 -> inputs.py
 -> optimizer.py
 -> validator.py
 -> cad_spec.py
 -> Autodesk AutoCAD Automation adapter

This module does not contain UDCPR table numbers or regulatory values.
It does not use an LLM for regulatory decisions.

Important:
- Missing regulatory inputs are not invented.
- Irregular plot geometry must be supplied as real geometry before CAD generation.
- Parking bay/circulation dimensions are configurable design assumptions and
  must be validated against the project's authoritative requirements.
- AutoCAD is the CAD executor, not the UDCPR decision engine.
