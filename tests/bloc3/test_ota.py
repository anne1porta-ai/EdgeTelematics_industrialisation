import hashlib
import json

import pytest

from src.ota import check_manifest, simulate_update


def test_manifest_is_valid():
    result = check_manifest.validate_manifest()
    assert result["checksum_valid"] is True
    assert result["signature_valid"] is True


def test_successful_update(tmp_path, monkeypatch):
    monkeypatch.setattr(simulate_update, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(simulate_update, "STATUS_PATH", tmp_path / "status.json")

    result = simulate_update.simulate_update("2.3.0")

    assert result == {
        "status": "success",
        "previous_version": "2.2.0",
        "current_version": "2.3.0",
    }


def test_failed_update_rolls_back(tmp_path, monkeypatch):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"current_version": "2.3.0"}), encoding="utf-8")
    monkeypatch.setattr(simulate_update, "STATE_PATH", state)
    monkeypatch.setattr(simulate_update, "STATUS_PATH", tmp_path / "status.json")

    result = simulate_update.simulate_update("2.4.0", fail_install=True)

    assert result == {
        "status": "rolled_back",
        "attempted_version": "2.4.0",
        "current_version": "2.3.0",
        "previous_version": "2.3.0",
    }
    assert json.loads(state.read_text(encoding="utf-8"))["current_version"] == "2.3.0"


def test_altered_package_is_rejected_before_any_state_change(tmp_path, monkeypatch):
    state = tmp_path / "state.json"
    status = tmp_path / "status.json"
    state.write_text('{"current_version": "2.3.0"}', encoding="utf-8")
    status.write_text('{"status": "previous_success"}', encoding="utf-8")
    previous_state = state.read_bytes()
    previous_status = status.read_bytes()
    monkeypatch.setattr(simulate_update, "STATE_PATH", state)
    monkeypatch.setattr(simulate_update, "STATUS_PATH", status)

    package = tmp_path / "greenmove.zip"
    package.write_bytes(b"original package contents")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": "2.4.0",
                "commit": "demo-commit",
                "package": package.name,
                "checksum": hashlib.sha256(package.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    assert check_manifest.verify_package(manifest)["version"] == "2.4.0"
    package.write_bytes(b"altered package contents")

    with pytest.raises(ValueError, match="checksum"):
        simulate_update.simulate_update(manifest_path=manifest)

    assert state.read_bytes() == previous_state
    assert status.read_bytes() == previous_status
