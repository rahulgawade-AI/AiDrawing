# Product Requirements Document (PRD)

# AI Town Planning & Building Approval Assistant

Version: 2.0

Status: Draft

---

# 1. Purpose

The objective of this project is to build an AI-powered engineering assistant capable of:

- Understanding building regulations
- Understanding plot information
- Understanding development plans
- Understanding building plans
- Verifying compliance
- Generating engineering reports
- Assisting architects in preparing compliant building layouts

The system is intended to assist—not replace—qualified architects and engineers.

---

# 2. Vision

The application should answer one fundamental question:

> Can this building be legally constructed on this plot?

To answer this, the system combines:

• Regulations

• Engineering calculations

• Computer Vision

• GIS

• Artificial Intelligence

---

# 3. Target Users

## Architect

Needs

- Fast regulation lookup
- FSI calculations
- Compliance checking
- Layout suggestions

---

## Civil Engineer

Needs

- Engineering validation
- Setback calculations
- Parking calculations

---

## Developer

Needs

- Feasibility analysis
- Maximum permissible built-up area
- Project optimization

---

## Planning Authority

Needs

- Automated scrutiny
- Compliance verification
- Report generation

---

## Student

Needs

- Learn regulations
- Ask questions
- Understand engineering concepts

---

# 4. Functional Requirements

## Module 1

AI Regulation Assistant

### Inputs

Natural language question

### Outputs

- Accurate answer
- Applicable regulations
- References
- Related regulations

---

## Module 2

Plot Intelligence

### Inputs

- Plot image
- Survey plan
- Village map
- DP Plan

### Outputs

- Plot dimensions
- Plot area
- Road width
- Zone
- Reservation
- Geometry

---

## Module 3

Building Plan Analysis

### Inputs

- PDF
- Image
- CAD (future)

### Outputs

- Floors
- Rooms
- Staircases
- Parking
- Lift
- Building footprint
- Dimensions

---

## Module 4

Engineering Engine

The application shall calculate

- FSI
- Ground Coverage
- Setbacks
- Parking
- Height
- Fire Access
- Open Spaces
- Loading Rules

These calculations shall be deterministic.

No LLM shall perform engineering calculations.

---

## Module 5

Compliance Checker

The application shall verify

- FSI
- Setbacks
- Parking
- Fire
- Height
- Coverage
- Accessibility

Output

PASS

FAIL

WARNING

Applicable Regulation

Recommendation

---

## Module 6

Layout Generator

Input

- Plot
- Applicable regulations
- User requirements

Output

- Site layout
- Parking layout
- Floor plans
- Compliance score

---

# 5. AI Responsibilities

## Ollama

Responsible for

- Regulation extraction
- OCR assistance
- Plan understanding
- Plot understanding
- Knowledge generation

Runs locally.

---

## GPT-5

Responsible for

- Question answering
- Multi-regulation reasoning
- Compliance explanation
- Design suggestions

GPT shall never perform engineering calculations.

---

# 6. Engineering Principles

Engineering calculations shall always be deterministic.

Every result shall be traceable to one or more regulations.

Every engineering decision shall be reproducible.

---

# 7. GIS Requirements

The application shall support

- Village Maps
- Development Plans
- GIS Layers
- Road Network
- Reservations
- Zones

The GIS engine shall automatically determine applicable planning constraints whenever possible.

---

# 8. Rule Engine

Every regulation shall eventually be represented as machine-readable rules.

Example

Road Width

↓

Applicable Setback

↓

Applicable FSI

↓

Applicable Height

Rules shall be version controlled.

---

# 9. Knowledge Base

The application includes built-in knowledge.

Users shall NOT upload regulations.

Supported sources

- UDCPR
- NBC
- Fire Regulations
- Government Resolutions
- Circulars

---

# 10. Non-functional Requirements

The application shall be

- Modular
- Extensible
- Testable
- Explainable
- Auditable

---

# 11. Future Features

- DWG Support
- 3D Building Models
- Cost Estimation
- BOQ Generation
- Structural Design Assistance
- Approval Workflow
- Digital Signatures
- Municipal Integration

---

# 12. Success Criteria

The application should be capable of

✓ Answering regulation questions

✓ Calculating engineering parameters

✓ Checking compliance

✓ Explaining violations

✓ Suggesting corrections

✓ Generating preliminary layouts

---

# 13. Out of Scope (Version 2.0)

The following are intentionally excluded from the first release:

- Automatic municipal submission
- Structural analysis
- HVAC design
- Electrical design
- Plumbing design
- Reinforcement detailing
- BIM authoring
- Final architectural drawings suitable for construction

These may be considered in future versions.
