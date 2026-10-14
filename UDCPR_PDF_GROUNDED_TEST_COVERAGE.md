# UDCPR PDF-Grounded Test Coverage

Source: UDCPR-2020 Maharashtra, updated through 30 January 2024.

The functional test is intentionally data-driven: regulatory values are expected from PostgreSQL populated from the UDCPR source. Production code does not embed UDCPR numeric thresholds.

## Covered for the residential Pune test scenario

- Regulation 6.2.1 / Table 6-D: road-width-driven minimum plot/setback/marginal requirements.
- Regulation 6.3 / Table 6-G: basic FSI, premium FSI, TDR loading, maximum building potential.
- Regulation 8.2.1 / Table 8-B: residential parking based on tenement carpet area.
- Regulation 8.2.2 / Table 8-C: planning-authority parking multiplying factor.
- Regulation 9.14: balcony rules are source requirements and should be resolved through the regulatory-rule layer when selected.
- Regulation 9.20: lighting/ventilation requirements and Table 9-C are source requirements for dependent building-height cases.
- Regulation 9.31: housing-scheme requirements are conditional on the number of flats/tenements.
- Regulation 9.32: special-building fire-safety requirement is conditional and references the Maharashtra Fire Prevention and Life Safety Measures Act, 2006 and NBC Part IV.
- Regulation 13.1.4: barrier-free access requirements are source requirements for accessible building design.

## Test assumptions

- Road width: 12.0 m.
- Flat/carpet area: 750 sq ft per test tenement, converted to square metres for table matching.
- Maximum FSI: not an input; it is copied into the test target only after PostgreSQL returns it.

## Important boundary

Chroma/OpenAI may select the governing regulation/table. After that selection, the authoritative-value boundary is PostgreSQL. No AI call is permitted after selection.
