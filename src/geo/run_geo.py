import json
from collections.abc import Callable

from src.geo.geo_engine import (
    calculate_bounding_box,
    is_point_in_zfe,
    load_json_file,
)

POLYGON_FILE = "data/lyon_polygon.json"
GPS_FILE = "data/truck_gps.json"


def run_geo_engine(
    *,
    on_event: Callable[[dict], None] | None = None,
    polygon_file: str = POLYGON_FILE,
    gps_file: str = GPS_FILE,
    raise_on_error: bool = False,
) -> None:
    """Run ZFE detection; publish each OUT-to-IN event before logging it.

    The optional callback is local persistence, not network transmission.
    Its failures deliberately propagate instead of being reported as bad GPS.
    Enable raise_on_error when an incomplete acquisition must fail its caller.
    """
    try:
        polygon = load_json_file(polygon_file)
        gps_points = iter(load_json_file(gps_file))
        bbox = calculate_bounding_box(polygon)
    except FileNotFoundError as error:
        if raise_on_error:
            raise
        print(f"[ERROR] {error}")
        return
    except json.JSONDecodeError as error:
        if raise_on_error:
            raise
        print(f"[ERROR] Invalid JSON data: {error}")
        return
    except (KeyError, TypeError, ValueError) as error:
        if raise_on_error:
            raise
        print(f"[ERROR] Invalid Geo input data: {error}")
        return

    was_inside = False
    for point in gps_points:
        event = None
        try:
            is_inside = is_point_in_zfe(point, polygon, bbox)
            if is_inside and not was_inside:
                event = {
                    "id": point["id"],
                    "timestamp": point["timestamp"],
                    "lat": point["lat"],
                    "lon": point["lon"],
                }
                message = (
                    f"[ALERT ZFE] id={point['id']} "
                    f"time={point['timestamp']} "
                    f"lat={point['lat']} lon={point['lon']}"
                )
            elif is_inside:
                message = f"[GPS IN] id={point['id']} time={point['timestamp']}"
            else:
                message = f"[GPS OUT] id={point['id']} time={point['timestamp']}"

        except (KeyError, TypeError, ValueError) as error:
            if raise_on_error:
                raise
            print(f"[ERROR] Invalid Geo input data: {error}")
            return

        if event is not None and on_event is not None:
            on_event(event)
        print(message)
        was_inside = is_inside


if __name__ == "__main__":
    run_geo_engine()
