import json

import pytest

from src.safety.safety_engine import (
    analyze_accelerometer_stream,
    build_daily_score,
    detect_harsh_braking_events,
    is_harsh_braking,
    iter_accelerometer_data,
    write_daily_score,
)


def test_ignores_normal_driving_noise():
    assert is_harsh_braking(0.05) is False
    assert is_harsh_braking(-0.80) is False
    assert is_harsh_braking(-1.20) is False


def test_detects_harsh_braking():
    assert is_harsh_braking(-3.45) is True


def test_threshold_is_strict():
    assert is_harsh_braking(-2.5) is False
    assert is_harsh_braking(-2.51) is True


def test_detect_harsh_braking_events():
    samples = [
        {"timestamp": 1, "acc_x": 0.1, "acc_y": 0.05, "acc_z": 9.81},
        {"timestamp": 2, "acc_x": 0.2, "acc_y": -3.45, "acc_z": 9.65},
        {"timestamp": 3, "acc_x": 0.1, "acc_y": -0.50, "acc_z": 9.79},
    ]

    events = detect_harsh_braking_events(samples)

    assert len(events) == 1
    assert events[0]["timestamp"] == 2
    assert events[0]["acc_y"] == -3.45


def test_iter_accelerometer_data_missing_file(tmp_path):
    missing_file = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        list(iter_accelerometer_data(str(missing_file)))


def test_iter_accelerometer_data_invalid_value(tmp_path):
    invalid_file = tmp_path / "invalid.csv"
    invalid_file.write_text(
        "timestamp,acc_x,acc_y,acc_z\n"
        "1678880000,0.12,invalid,9.81\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        list(iter_accelerometer_data(str(invalid_file)))


def test_build_daily_score():
    samples = [
        {"timestamp": 1, "acc_x": 0.1, "acc_y": 0.05, "acc_z": 9.81},
        {"timestamp": 2, "acc_x": 0.2, "acc_y": -3.45, "acc_z": 9.65},
    ]
    events = [samples[1]]

    score = build_daily_score(samples, events)

    assert score == {
        "total_samples": 2,
        "harsh_braking_events": 1,
        "events": [
            {
                "timestamp": 2,
                "acc_y": -3.45,
            }
        ],
    }


def test_write_daily_score(tmp_path):
    output_file = tmp_path / "daily_score.json"
    score = {
        "total_samples": 10,
        "harsh_braking_events": 1,
        "events": [
            {
                "timestamp": 1678880005,
                "acc_y": -3.45,
            }
        ],
    }

    write_daily_score(score, str(output_file))

    with output_file.open("r", encoding="utf-8") as file:
        saved_score = json.load(file)

    assert saved_score == score

def test_iter_accelerometer_data_reads_samples(tmp_path):
    csv_file = tmp_path / "samples.csv"
    csv_file.write_text(
        "timestamp,acc_x,acc_y,acc_z\n"
        "1,0.12,0.05,9.81\n"
        "2,0.25,-3.45,9.65\n",
        encoding="utf-8",
    )

    samples = list(iter_accelerometer_data(str(csv_file)))

    assert len(samples) == 2
    assert samples[0]["acc_y"] == 0.05
    assert samples[1]["acc_y"] == -3.45


def test_analyze_accelerometer_stream():
    samples = iter(
        [
            {"timestamp": 1, "acc_x": 0.1, "acc_y": 0.05, "acc_z": 9.81},
            {"timestamp": 2, "acc_x": 0.2, "acc_y": -3.45, "acc_z": 9.65},
            {"timestamp": 3, "acc_x": 0.1, "acc_y": -0.50, "acc_z": 9.79},
        ]
    )

    score = analyze_accelerometer_stream(samples)

    assert score == {
        "total_samples": 3,
        "harsh_braking_events": 1,
        "events": [
            {
                "timestamp": 2,
                "acc_y": -3.45,
            }
        ],
    }