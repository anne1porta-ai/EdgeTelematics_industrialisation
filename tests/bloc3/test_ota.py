import json

from src.ota import check_manifest
from src.ota import simulate_update


def test_manifest_is_valid():
    result = (
        check_manifest.validate_manifest()
    )

    assert (
        result["checksum_valid"]
        is True
    )

    assert (
        result["signature_valid"]
        is True
    )


def test_successful_update(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        simulate_update,
        "STATE_PATH",
        tmp_path / "state.json",
    )

    monkeypatch.setattr(
        simulate_update,
        "STATUS_PATH",
        tmp_path / "status.json",
    )

    result = (
        simulate_update
        .simulate_update("2.3.0")
    )

    assert (
        result["status"]
        == "success"
    )


def test_failed_update_rolls_back(
    tmp_path,
    monkeypatch,
):
    state = (
        tmp_path / "state.json"
    )

    state.write_text(
        json.dumps(
            {
                "current_version":
                    "2.3.0"
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        simulate_update,
        "STATE_PATH",
        state,
    )

    monkeypatch.setattr(
        simulate_update,
        "STATUS_PATH",
        tmp_path / "status.json",
    )

    result = (
        simulate_update
        .simulate_update(
            "2.4.0",
            fail_install=True,
        )
    )

    assert (
        result["status"]
        == "rolled_back"
    )

    assert (
        result["current_version"]
        == "2.3.0"
    )