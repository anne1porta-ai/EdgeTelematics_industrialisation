"""Classer des positions GPS par rapport à un polygone ZFE."""

import json
from pathlib import Path


def load_json_file(file_path):
    """Lire un fichier JSON et retourner la liste qu'il contient."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_bounding_box(polygon):
    """Calculer le plus petit rectangle qui contient le polygone."""
    latitudes = []
    longitudes = []

    for point in polygon:
        latitudes.append(point["lat"])
        longitudes.append(point["lon"])

    return {
        "min_lat": min(latitudes),
        "max_lat": max(latitudes),
        "min_lon": min(longitudes),
        "max_lon": max(longitudes),
    }


def is_inside_bounding_box(point, bbox):
    """Vérifier si le point se trouve dans la Bounding Box, bord compris."""
    latitude_ok = bbox["min_lat"] <= point["lat"] <= bbox["max_lat"]
    longitude_ok = bbox["min_lon"] <= point["lon"] <= bbox["max_lon"]
    return latitude_ok and longitude_ok


def is_point_on_segment(point, start, end, tolerance=1e-9):
    """Vérifier si le point se trouve sur le segment."""
    px = point["lon"]
    py = point["lat"]
    ax = start["lon"]
    ay = start["lat"]
    bx = end["lon"]
    by = end["lat"]

    # Le produit vectoriel vaut presque zéro si les trois points sont alignés.
    cross_product = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross_product) > tolerance:
        return False

    inside_x = min(ax, bx) - tolerance <= px <= max(ax, bx) + tolerance
    inside_y = min(ay, by) - tolerance <= py <= max(ay, by) + tolerance
    return inside_x and inside_y


def is_point_inside_polygon(point, polygon):
    """Utiliser le Ray Casting pour tester l'intérieur du polygone."""
    x = point["lon"]
    y = point["lat"]
    inside = False
    previous_index = len(polygon) - 1

    for current_index in range(len(polygon)):
        current = polygon[current_index]
        previous = polygon[previous_index]

        # Dans ce projet, le contour fait partie de la ZFE.
        if is_point_on_segment(point, previous, current):
            return True

        current_x = current["lon"]
        current_y = current["lat"]
        previous_x = previous["lon"]
        previous_y = previous["lat"]

        crosses_height = (current_y > y) != (previous_y > y)
        if crosses_height:
            crossing_x = (
                (previous_x - current_x)
                * (y - current_y)
                / (previous_y - current_y)
                + current_x
            )
            if x < crossing_x:
                inside = not inside

        previous_index = current_index

    return inside


def is_point_in_zfe(point, polygon, bbox):
    """Rejeter d'abord par Bounding Box, puis vérifier le polygone réel."""
    if not is_inside_bounding_box(point, bbox):
        return False

    return is_point_inside_polygon(point, polygon)
