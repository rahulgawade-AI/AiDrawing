Sprint 1 (Foundation)
Project skeleton
PostgreSQL
Configuration
Logging
LangGraph setup
Knowledge ingestion workflow
Sprint 2 (Knowledge)
Regulation extraction
Knowledge Cards
Embeddings
Search
GPT Q&A
Sprint 3 (Vision)
Plot reader
Plan reader
Dimension extraction
OCR integration
Sprint 4 (Engineering)
Rule engine
FSI engine
Setback engine
Parking engine
Height engine
Sprint 5 (Compliance)
Compliance checker
Report generation
GPT explanations
Sprint 6 (Design)
Layout generation
Floor planning
Site planning
Drawing export


Rvevised roadmap
Sprint 1  ✅

Sprint 2  ✅

Sprint 3
    Vision
    OCR
    Plot Reader
    Plan Reader
    Geometry

Sprint 4
    Engineering
    Rule Engine
    FSI
    Setback
    Parking
    Height

    <-- Build shared services here

Sprint 5
    Compliance

Sprint 6
    Design


Future for workflow
workflows/

common/

question_answering/

plot_analysis/

building_plan/

compliance/

layout_generation/


                AI Town Planning Platform
────────────────────────────────────────────────────

Vision
  │
  ▼
Site Model
  │
  ▼
Engineering Engine
  │
  ▼
Layout Optimizer
  │
  ▼
Building Information Model (BIM)
  │
  ├──────────► DXF
  ├──────────► DWG
  ├──────────► SVG
  ├──────────► PDF
  ├──────────► IFC (future)
  └──────────► AutoCAD / BricsCAD


  For building engine final architecture
                      AI Town Planning Platform

                +---------------------------+
                |        FastAPI            |
                +---------------------------+
                            |
            +---------------+----------------+
            |                                |
     Knowledge Engine                 Vision Engine
     (Completed)                      (Sprint 3)
            |                                |
            +---------------+----------------+
                            |
                      Site Model
                            |
                    Engineering Engine
                            |
                   Layout Optimization
                            |
                     Building Model
                            |
        +----------+----------+-----------+-----------+
        |          |          |           |           |
       DXF        SVG        PDF         IFC       3D Model



       Sprint 3
─────────
OpenCV
OCR
Geometry
(No AI Training)

↓

Sprint 4
─────────
Engineering
UDCPR Rules

↓

Sprint 5
─────────
Layout Generator

↓

Sprint 6
─────────
Train YOLO
Replace:
DoorDetector
WindowDetector
ParkingDetector
StaircaseDetector

↓

Sprint 7
─────────
Train Floor Plan Generator