"""Simulate OTA installation, status reporting and rollback behavior.

This module is a demonstration of the lifecycle expected from an OTA update.
It is not a production Android updater and does not implement atomic package
installation at operating-system level.
"""

import argparse
import json
from pathlib import Path


STATE_PATH = Path(
    "ota_state.json"
)

STATUS_PATH = Path(
    "ota_status.json"
)

DEFAULT_VERSION = "2.2.0"


def read_current_version() -> str:
    """Return the currently installed simulated version."""
    if not STATE_PATH.exists():
        return DEFAULT_VERSION

    content = json.loads(
        STATE_PATH.read_text(
            encoding="utf-8"
        )
    )

    return content["current_version"]


def write_current_version(
    version: str,
) -> None:
    """Persist the simulated current version."""
    STATE_PATH.write_text(
        json.dumps(
            {
                "current_version":
                    version
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_status(
    status: dict,
) -> None:
    """Persist the status that would normally be reported to the backend."""
    STATUS_PATH.write_text(
        json.dumps(
            status,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def simulate_update(
    version: str,
    fail_install: bool = False,
) -> dict:
    """Simulate a successful update or a rollback after installation failure."""
    previous = read_current_version()

    print(
        "[OTA] download complete "
        f"version={version}"
    )

    if fail_install:
        # Keep the last known healthy version active when installation fails.
        write_current_version(
            previous
        )

        status = {
            "status": "rolled_back",
            "attempted_version":
                version,
            "current_version":
                previous,
            "previous_version":
                previous,
        }

        write_status(status)

        print(
            "[OTA] install failed "
            f"version={version} "
            f"-> rollback to {previous}"
        )

        print(
            "[OTA] status reported "
            "to backend"
        )

        return status

    write_current_version(version)

    status = {
        "status": "success",
        "previous_version":
            previous,
        "current_version":
            version,
    }

    write_status(status)

    print(
        "[OTA] install success "
        f"previous={previous} "
        f"current={version}"
    )

    print(
        "[OTA] status reported "
        "to backend"
    )

    return status


def main() -> None:
    """Parse CLI arguments and execute the OTA simulation."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--version",
        required=True,
    )

    parser.add_argument(
        "--fail-install",
        action="store_true",
    )

    args = parser.parse_args()

    simulate_update(
        args.version,
        fail_install=args.fail_install,
    )


if __name__ == "__main__":
    main()