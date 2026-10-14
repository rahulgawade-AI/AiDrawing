#!/bin/bash

set -e

BASE="modules"

echo "Creating Sprint 3 Vision Architecture..."

mkdir -p ${BASE}/vision/{domain,parsers,ocr,detectors,geometry,builders,pipelines,services,repositories}
mkdir -p ${BASE}/site/{domain,services,repositories}
mkdir -p ${BASE}/building/domain

#
# Vision Domain
#

touch ${BASE}/vision/domain/__init__.py

for file in \
point \
line \
polygon \
rectangle \
bounding_box \
text_block \
dimension \
drawing \
page \
image \
plot_boundary \
road \
north_arrow \
scale
do
    touch ${BASE}/vision/domain/${file}.py
done

#
# Parsers
#

touch ${BASE}/vision/parsers/__init__.py

for file in \
document_parser \
pdf_parser \
image_parser \
cad_parser
do
    touch ${BASE}/vision/parsers/${file}.py
done

#
# OCR
#

touch ${BASE}/vision/ocr/__init__.py

for file in \
ocr_service \
paddle_ocr \
text_cleaner \
dimension_parser
do
    touch ${BASE}/vision/ocr/${file}.py
done

#
# Detectors
#

touch ${BASE}/vision/detectors/__init__.py

for file in \
plot_detector \
road_detector \
wall_detector \
room_detector \
door_detector \
window_detector \
staircase_detector \
parking_detector \
north_detector \
scale_detector
do
    touch ${BASE}/vision/detectors/${file}.py
done

#
# Geometry
#

touch ${BASE}/vision/geometry/__init__.py

for file in \
geometry_service \
polygon_builder \
topology_builder \
coordinate_transform \
measurement_service
do
    touch ${BASE}/vision/geometry/${file}.py
done

#
# Builders
#

touch ${BASE}/vision/builders/__init__.py

for file in \
site_model_builder
do
    touch ${BASE}/vision/builders/${file}.py
done

#
# Pipelines
#

touch ${BASE}/vision/pipelines/__init__.py

for file in \
vision_pipeline
do
    touch ${BASE}/vision/pipelines/${file}.py
done

#
# Services
#

touch ${BASE}/vision/services/__init__.py

for file in \
vision_service
do
    touch ${BASE}/vision/services/${file}.py
done

#
# Repositories
#

touch ${BASE}/vision/repositories/__init__.py

#
# Site Domain
#

touch ${BASE}/site/domain/__init__.py

for file in \
site_model \
zoning \
planning_zone \
reservation \
road \
utility
do
    touch ${BASE}/site/domain/${file}.py
done

#
# Site Services
#

touch ${BASE}/site/services/__init__.py

for file in \
site_service \
zoning_service \
reservation_service \
road_service
do
    touch ${BASE}/site/services/${file}.py
done

#
# Site Repository
#

touch ${BASE}/site/repositories/__init__.py

for file in \
planning_map_repository
do
    touch ${BASE}/site/repositories/${file}.py
done

#
# Building Domain
#

touch ${BASE}/building/domain/__init__.py

for file in \
building \
floor \
room \
wall \
door \
window \
staircase \
parking \
column \
beam \
slab \
roof
do
    touch ${BASE}/building/domain/${file}.py
done

echo ""
echo "======================================="
echo " Sprint 3 structure created successfully"
echo "======================================="
