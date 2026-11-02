from src.safety.safety_engine import analyze_accelerometer_stream


def make_samples(values):
    return [
        {"timestamp": index, "acc_x": 0.1, "acc_y": value, "acc_z": 9.81}
        for index, value in enumerate(values)
    ]


def test_plateau_emits_one_alert_and_counts_every_sample():
    samples = make_samples([-3.0, -3.1, -4.0, -3.0, -2.6])

    score = analyze_accelerometer_stream(iter(samples))

    assert score == {
        "total_samples": 5,
        "harsh_braking_events": 1,
        "events": [{"timestamp": 0, "acc_y": -3.0}],
    }


def test_threshold_equalities_and_band_preserve_state_until_strict_rearming():
    samples = make_samples(
        [-2.5, -2.4, -2.3, -2.51, -2.5, -2.4, -2.3, -3.0, -2.29, -2.3, -2.5, -2.51]
    )

    score = analyze_accelerometer_stream(iter(samples))

    assert score["total_samples"] == 12
    assert score["harsh_braking_events"] == 2
    assert score["events"] == [
        {"timestamp": 3, "acc_y": -2.51},
        {"timestamp": 11, "acc_y": -2.51},
    ]


def test_two_stream_runs_produce_the_same_events():
    samples = make_samples([0.0, -3.0, -3.4, -2.4, -2.3, -2.2, -2.5, -3.5])

    first = analyze_accelerometer_stream(iter(samples))
    second = analyze_accelerometer_stream(iter(samples))

    assert first == second
    assert first["events"] == [
        {"timestamp": 1, "acc_y": -3.0},
        {"timestamp": 7, "acc_y": -3.5},
    ]


def test_callback_is_immediate_without_retaining_events():
    emitted = []
    samples = make_samples([-3.0, -3.4, -2.3, -2.2, -3.1])

    def stream():
        yield samples[0]
        assert emitted == [{"timestamp": 0, "acc_y": -3.0}]
        yield samples[1]
        yield samples[2]
        yield samples[3]
        assert len(emitted) == 1
        yield samples[4]

    score = analyze_accelerometer_stream(
        stream(), on_event=emitted.append, retain_events=False
    )

    assert score == {"total_samples": 5, "harsh_braking_events": 2, "events": []}
    assert emitted == [
        {"timestamp": 0, "acc_y": -3.0},
        {"timestamp": 4, "acc_y": -3.1},
    ]
