"""Lire la trace GPS et produire un événement lors d'une entrée en ZFE."""

import json
from pathlib import Path

from src.geo.geo_engine import (
    calculate_bounding_box,
    is_point_in_zfe,
    load_json_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLYGON_FILE = PROJECT_ROOT / "data" / "lyon_polygon.json"
GPS_FILE = PROJECT_ROOT / "data" / "truck_gps.json"


def run_geo_engine(
    on_event=None,
    polygon_file=POLYGON_FILE,
    gps_file=GPS_FILE,
    raise_on_error=False,
):
    """Analyser la trace et publier une alerte lors du passage OUT vers IN."""
    try:
        polygon = load_json_file(polygon_file)
        gps_points = load_json_file(gps_file)
        bbox = calculate_bounding_box(polygon)
    except FileNotFoundError as error:
        if raise_on_error:
            raise
        print(f"[ERROR] {error}")
        return {"positions": 0, "entries": 0}
    except json.JSONDecodeError as error:
        if raise_on_error:
            raise
        print(f"[ERROR] Invalid JSON data: {error}")
        return {"positions": 0, "entries": 0}
    except (KeyError, TypeError, ValueError) as error:
        if raise_on_error:
            raise
        print(f"[ERROR] Invalid Geo input data: {error}")
        return {"positions": 0, "entries": 0}

    was_inside = False
    positions = 0
    entries = 0

    for point in gps_points:
        positions += 1

        try:
            is_inside = is_point_in_zfe(point, polygon, bbox)

            if is_inside and not was_inside:
                event = {
                    "id": point["id"],
                    "timestamp": point["timestamp"],
                    "lat": point["lat"],
                    "lon": point["lon"],
                }
                entries += 1
                if on_event is not None:
                    on_event(event)

                print(
                    f"[ALERT ZFE] id={point['id']} "
                    f"time={point['timestamp']} "
                    f"lat={point['lat']} lon={point['lon']}"
                )
            elif is_inside:
                print(f"[GPS IN] id={point['id']} time={point['timestamp']}")
            else:
                print(f"[GPS OUT] id={point['id']} time={point['timestamp']}")

            was_inside = is_inside

        except (KeyError, TypeError, ValueError) as error:
            if raise_on_error:
                raise
            print(f"[ERROR] Invalid Geo input data: {error}")
            return {"positions": positions, "entries": entries}

    return {"positions": positions, "entries": entries}


if __name__ == "__main__":
    run_geo_engine()
