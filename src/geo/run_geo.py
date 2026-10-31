import json

from src.geo.geo_engine import (
    calculate_bounding_box,
    is_point_in_zfe,
    load_json_file,
)


POLYGON_FILE = "data/lyon_polygon.json"
GPS_FILE = "data/truck_gps.json"


def run_geo_engine() -> None:
    """Run the offline ZFE detection engine on the simulated GPS trace."""
    try:
        polygon = load_json_file(POLYGON_FILE)
        gps_points = load_json_file(GPS_FILE)
        bbox = calculate_bounding_box(polygon)

        was_inside = False

        for point in gps_points:
            is_inside = is_point_in_zfe(point, polygon, bbox)

            if is_inside and not was_inside:
                print(
                    f'[ALERT ZFE] id={point["id"]} '
                    f'time={point["timestamp"]} '
                    f'lat={point["lat"]} lon={point["lon"]}'
                )
            elif is_inside:
                print(
                    f'[GPS IN] id={point["id"]} '
                    f'time={point["timestamp"]}'
                )
            else:
                print(
                    f'[GPS OUT] id={point["id"]} '
                    f'time={point["timestamp"]}'
                )

            was_inside = is_inside

    except FileNotFoundError as error:
        print(f"[ERROR] {error}")
    except json.JSONDecodeError as error:
        print(f"[ERROR] Invalid JSON data: {error}")
    except (KeyError, TypeError, ValueError) as error:
        print(f"[ERROR] Invalid Geo input data: {error}")


if __name__ == "__main__":
    run_geo_engine()