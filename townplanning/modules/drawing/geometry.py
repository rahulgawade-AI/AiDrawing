from __future__ import annotations

def rectangular_buildable_area(width, depth, front, rear, left, right):
    vals = (width, depth, front, rear, left, right)
    if any(v is None for v in vals):
        return None
    w = max(0.0, float(width) - float(left) - float(right))
    d = max(0.0, float(depth) - float(front) - float(rear))
    return w * d

def require_real_boundary(boundary):
    if boundary is None:
        return None
    return boundary
