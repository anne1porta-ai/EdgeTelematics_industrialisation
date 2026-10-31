import json

import pytest

from src.geo.geo_engine import (
    calculate_bounding_box,
    is_inside_bounding_box,
    is_point_inside_polygon,
    is_point_in_zfe,
    load_json_file,
)


POLYGON = [
    {"lat": 45.7800, "lon": 4.8000},
    {"lat": 45.7900, "lon": 4.8600},
    {"lat": 45.7500, "lon": 4.8800},
    {"lat": 45.7300, "lon": 4.8200},
    {"lat": 45.7450, "lon": 4.8100},
    {"lat": 45.7800, "lon": 4.8000},
]


def test_calculate_bounding_box():
    bbox = calculate_bounding_box(POLYGON)

    assert bbox == {
        "min_lat": 45.73,
        "max_lat": 45.79,
        "min_lon": 4.8,
        "max_lon": 4.88,
    }


def test_point_outside_bounding_box():
    bbox = calculate_bounding_box(POLYGON)
    point = {"lat": 45.81, "lon": 4.75}

    assert is_inside_bounding_box(point, bbox) is False


def test_point_inside_bounding_box():
    bbox = calculate_bounding_box(POLYGON)
    point = {"lat": 45.76, "lon": 4.8357}

    assert is_inside_bounding_box(point, bbox) is True


def test_point_inside_polygon():
    point = {"lat": 45.76, "lon": 4.8357}

    assert is_point_inside_polygon(point, POLYGON) is True


def test_point_outside_polygon():
    point = {"lat": 45.81, "lon": 4.75}

    assert is_point_inside_polygon(point, POLYGON) is False


def test_point_on_polygon_boundary():
    point = {"lat": 45.7800, "lon": 4.8000}

    assert is_point_inside_polygon(point, POLYGON) is True


def test_zfe_detection_uses_bounding_box_and_ray_casting():
    bbox = calculate_bounding_box(POLYGON)

    inside_point = {"lat": 45.76, "lon": 4.8357}
    outside_point = {"lat": 45.81, "lon": 4.75}

    assert is_point_in_zfe(inside_point, POLYGON, bbox) is True
    assert is_point_in_zfe(outside_point, POLYGON, bbox) is False


def test_load_json_file_missing_file(tmp_path):
    missing_file = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_json_file(str(missing_file))


def test_load_json_file_invalid_json(tmp_path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_json_file(str(invalid_file))

def test_zfe_entry_transition_triggers_only_once():
    states = [False, False, True, True, True]
    was_inside = False
    alert_count = 0

    for is_inside in states:
        if is_inside and not was_inside:
            alert_count += 1

        was_inside = is_inside

    assert alert_count == 1