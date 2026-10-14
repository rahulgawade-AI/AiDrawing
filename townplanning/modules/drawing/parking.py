from __future__ import annotations
import math
from .models import ParkingDesign, RegulatoryInputs

def visitor_spaces(value, base: int) -> int:
    if isinstance(value, str) and "%" in value:
        try:
            return math.ceil(base * float(value.replace("%", "")) / 100)
        except ValueError:
            return 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0

def estimate_parking(regulatory: RegulatoryInputs, strategy="surface"):
    cars = max(0, regulatory.car_parking_required or 0)
    two = max(0, regulatory.two_wheeler_parking_required or 0)
    visitors = visitor_spaces(regulatory.visitor_parking_required, cars + two)
    car_area = cars * 2.5 * 5.0
    two_area = two * 1.0 * 2.0
    circulation = (car_area + two_area) * 0.35
    return ParkingDesign(
        car_spaces=cars,
        two_wheeler_spaces=two,
        visitor_spaces=visitors,
        car_bay_area_m2=car_area,
        two_wheeler_bay_area_m2=two_area,
        circulation_area_m2=circulation,
        total_area_m2=car_area + two_area + circulation,
        strategy=strategy,
    )
