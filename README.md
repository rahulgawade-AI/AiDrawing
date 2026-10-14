# AI Town Planning & Building Approval Assistant

> **An AI-powered platform for Urban Planning, Building Regulation Compliance, Plot Analysis, and Intelligent Layout Generation.**

---

# Vision

The objective of this project is to build an AI-powered assistant capable of understanding building regulations, analyzing land parcels, checking building plans against applicable regulations, and generating compliant building layouts.

Unlike traditional RAG applications, this system combines:

- Artificial Intelligence
- Computer Vision
- Rule-Based Engineering
- GIS
- Generative AI

to create a complete Building Approval Assistant.

---

# Problem Statement

Today architects and engineers spend significant time:

- Reading hundreds of pages of UDCPR
- Checking compliance manually
- Calculating FSI
- Checking setbacks
- Checking parking requirements
- Verifying fire regulations
- Understanding DP Plans
- Understanding Village Maps
- Preparing multiple layout revisions

This project aims to automate a significant portion of this workflow.

---

# Goals

The application should be able to:

✅ Answer questions from UDCPR

✅ Understand Building Regulations

✅ Understand Development Plans (DP)

✅ Understand Village Maps

✅ Understand Plot Geometry

✅ Calculate FSI

✅ Calculate Setbacks

✅ Calculate Parking Requirements

✅ Verify Building Plans

✅ Generate Compliance Reports

✅ Suggest Corrections

✅ Generate Building Layouts

---

# Core Features

## 1. AI Regulation Assistant

Users can ask natural language questions.

Examples

- What is FSI?
- Can I construct a basement?
- Is podium parking permitted?
- What parking is required for a commercial building?
- What is the minimum front setback?

The assistant retrieves relevant regulations and provides accurate, regulation-backed answers.

---

## 2. Plot Intelligence

Users upload

- Plot Layout
- Survey Plan
- Village Map
- DP Plan

The system automatically extracts

- Plot Boundary
- Plot Area
- Dimensions
- Road Width
- Orientation
- Existing Structures
- Adjacent Roads

---

## 3. Building Plan Compliance Checker

Users upload

- Floor Plans
- Site Plans
- Elevations
- Sections

The application checks

- FSI
- Setbacks
- Ground Coverage
- Parking
- Height
- Fire Regulations
- Accessibility
- Lift Requirements
- Staircase Width
- Open Spaces

The system generates a complete compliance report.

---

## 4. AI Layout Generator

Given

- Plot Geometry
- Applicable Regulations
- User Requirements

The application generates

- Site Layout
- Parking Layout
- Floor Plans
- Building Footprint
- Compliance Score

---

# High Level Architecture

```
                           USER

      Ask Question

      Upload Plot

      Upload Building Plan

                    │

                    ▼

             FastAPI Backend

                    │

             LangGraph Workflow

        ┌───────────┼────────────┐

        ▼           ▼            ▼

 Knowledge      Vision      Engineering

        │           │            │

     Chroma     OpenCV      Rule Engine

        │           │            │

        └───────────┼────────────┘

                    ▼

                  GPT-5

                    ▼

             Final Response
```

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Backend | FastAPI |
| Workflow | LangGraph |
| Local AI | Ollama |
| Cloud AI | GPT-5 |
| Embeddings | OpenAI |
| Vector Store | Chroma (PostgreSQL + pgvector later) |
| Database | PostgreSQL |
| Vision | OpenCV |
| OCR | PaddleOCR / Surya |
| GIS | GeoPandas |
| Geometry | Shapely |
| Frontend | React |

---

# AI Responsibilities

## Ollama

Used for

- Document Understanding
- Regulation Extraction
- Plot Analysis
- Plan Analysis
- Dimension Detection
- Knowledge Generation

Runs locally.

---

## GPT-5

Used for

- Question Answering
- Multi-Regulation Reasoning
- Compliance Explanation
- Design Suggestions
- Layout Planning

---

# Deterministic Engines

The following calculations are **never performed by AI**.

- FSI
- Setbacks
- Parking
- Fire Rules
- Ground Coverage
- Building Height
- Geometry
- Rule Validation

These are implemented as deterministic Python modules.

---

# Application Modules

```
app/

    api/

    workflows/

    knowledge/

    search/

    reasoning/

    vision/

    gis/

    engineering/

    compliance/

    drawing/

    database/

    models/

    tests/
```

---

# User Workflows

## Workflow 1

Ask Question

```
Question

↓

Retriever

↓

GPT

↓

Answer
```

---

## Workflow 2

Plot Analysis

```
Plot Image

↓

Vision AI

↓

Geometry

↓

Applicable Rules

↓

Engineering

↓

Summary
```

---

## Workflow 3

Building Plan Checker

```
Building Plan

↓

Vision

↓

Dimension Extraction

↓

Rule Engine

↓

Compliance Report

↓

GPT Explanation
```

---

## Workflow 4

Layout Generation

```
Plot

↓

Applicable Rules

↓

Engineering

↓

Planner

↓

Drawing Generator
```

---

# Rule Engine

All regulations are stored as machine-readable rules.

Example

```yaml
rule:
  front_setback

conditions:

  zone:
    Residential

  road_width:
    >=12

result:

  setback:
    6.0

reference:

  UDCPR 9.3.2
```

The compliance engine evaluates these rules instead of relying on an LLM.

---

# Testing Strategy

The project follows **functional testing** rather than unit testing every utility.

Examples

- test_knowledge_base.py
- test_question_answering.py
- test_plot_analysis.py
- test_fsi_engine.py
- test_compliance_checker.py
- test_layout_generator.py

Each test validates a complete business feature.

---

# Development Principles

1. AI understands; deterministic engines calculate.
2. Every compliance result must be traceable to the applicable regulation.
3. Every engineering calculation must be reproducible.
4. Regulations are ingested once and stored as structured knowledge.
5. Business features take priority over framework complexity.
6. Prefer simple, maintainable architecture over unnecessary abstractions.
7. Build modules that can evolve independently.

---

# Long-Term Vision

The long-term goal is to build an AI assistant capable of supporting architects, engineers, developers, planning authorities, and consultants throughout the building approval lifecycle.

Future capabilities include:

- Auto-generated building layouts
- Automatic FSI optimization
- Multi-objective layout optimization
- Building approval recommendations
- GIS integration
- CAD/DWG support
- 3D massing models
- Cost estimation
- BOQ generation
- Structural design assistance
- Approval workflow automation

---

# License

This project is intended for educational, research, and professional development purposes. Regulatory interpretations and engineering outputs should always be reviewed by qualified professionals before submission to any approving authority.
