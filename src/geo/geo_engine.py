import json
from pathlib import Path


def load_json_file(file_path: str) -> list[dict]:
    """Load and return JSON data from a file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_bounding_box(polygon: list[dict]) -> dict:
    """Calculate the minimum bounding box around a polygon."""
    latitudes = [point["lat"] for point in polygon]
    longitudes = [point["lon"] for point in polygon]

    return {
        "min_lat": min(latitudes),
        "max_lat": max(latitudes),
        "min_lon": min(longitudes),
        "max_lon": max(longitudes),
    }


def is_inside_bounding_box(point: dict, bbox: dict) -> bool:
    """Return True if a point is inside or on the bounding box."""
    return (
        bbox["min_lat"] <= point["lat"] <= bbox["max_lat"]
        and bbox["min_lon"] <= point["lon"] <= bbox["max_lon"]
    )

def is_point_on_segment(
    point: dict,
    start: dict,
    end: dict,
    tolerance: float = 1e-9,
) -> bool:
    """Return True if a point lies on a line segment."""
    px, py = point["lon"], point["lat"]
    ax, ay = start["lon"], start["lat"]
    bx, by = end["lon"], end["lat"]

    cross_product = (px - ax) * (by - ay) - (py - ay) * (bx - ax)

    if abs(cross_product) > tolerance:
        return False

    return (
        min(ax, bx) - tolerance <= px <= max(ax, bx) + tolerance
        and min(ay, by) - tolerance <= py <= max(ay, by) + tolerance
    )

def is_point_inside_polygon(point: dict, polygon: list[dict]) -> bool:
    """Return True if a point is inside or on the polygon boundary."""
    x = point["lon"]
    y = point["lat"]

    inside = False
    previous_index = len(polygon) - 1

    for current_index in range(len(polygon)):
        current = polygon[current_index]
        previous = polygon[previous_index]

        if is_point_on_segment(point, previous, current):
            return True

        current_x = current["lon"]
        current_y = current["lat"]
        previous_x = previous["lon"]
        previous_y = previous["lat"]

        intersects = (
            (current_y > y) != (previous_y > y)
            and x
            < (previous_x - current_x)
            * (y - current_y)
            / (previous_y - current_y)
            + current_x
        )

        if intersects:
            inside = not inside

        previous_index = current_index

    return inside

def is_point_in_zfe(point: dict, polygon: list[dict], bbox: dict) -> bool:
    """Return True if a point is inside the ZFE polygon."""
    # Quickly discard points outside the polygon bounding box.
    if not is_inside_bounding_box(point, bbox):
        return False

    return is_point_inside_polygon(point, polygon)