"""Relier la collecte aux evenements metier, a SQLite et au worker reseau."""

import argparse
import os
import threading
from collections import deque
from collections.abc import Iterable, Iterator
from typing import Any

import src.storage.event_repository as database
import src.sync.sync_service as network
from scripts.generate_demo_data import OUTPUT_FILE as STRESS_INPUT_FILE
from scripts.generate_demo_data import SAMPLE_COUNT, generate_demo_data
from src.domain.telemetry_event import TelemetryEvent
from src.geo.run_geo import run_geo_engine
from src.safety.run_safety import INPUT_FILE, run_safety_engine
from src.storage.event_repository import save_alert

# Historique RAM borne : les alertes importantes sont conservees dans SQLite.
recent_samples: deque[dict[str, int | float]] = deque(maxlen=600)


def _bounded_samples(
    samples: Iterable[dict[str, int | float]],
) -> Iterator[dict[str, int | float]]:
    for sample in samples:
        recent_samples.append(sample)
        yield sample


def save_braking(sample: dict[str, Any]) -> None:
    """Transformer un freinage en evenement metier avant persistance."""
    event = TelemetryEvent.harsh_braking(
        acc_y=float(sample["acc_y"]),
        timestamp=float(sample["timestamp"]),
    )
    save_alert(event)


def acquisition_loop(
    input_file: str = INPUT_FILE,
    output_file: str = "daily_score.json",
    *,
    samples: Iterable[dict[str, int | float]] | None = None,
) -> None:
    """Lire les capteurs, borner la RAM et stocker les alertes."""
    source = _bounded_samples(samples) if samples is not None else None

    run_safety_engine(
        input_file=input_file,
        output_file=output_file,
        on_event=save_braking,
        raise_on_error=True,
        samples=source,
        sample_buffer=recent_samples if samples is None else None,
    )


def save_zfe(point: dict[str, Any]) -> None:
    """Transformer une entree ZFE en evenement metier."""
    save_alert(TelemetryEvent.zfe_entry(point))


def collect_events(
    *,
    use_stress_dataset: bool = False,
    score_file: str = "daily_score.json",
    accelerometer_file: str | None = None,
) -> None:
    """Executer Geo et Safety ; le mode stress traite 1 000 mesures."""
    input_file = accelerometer_file or INPUT_FILE
    if use_stress_dataset:
        generate_demo_data()
        input_file = str(STRESS_INPUT_FILE)
        print(f"[STRESS] {SAMPLE_COUNT} mesures simulees seront traitees en flux.")

    run_geo_engine(on_event=save_zfe, raise_on_error=True)
    acquisition_loop(input_file, score_file)


def run_demo(
    use_stress_dataset: bool = False,
    *,
    db_path: str = "greenmove.db",
    api_url: str | None = None,
    sync_only: bool = False,
    score_file: str = "daily_score.json",
    wait_seconds: float = 5,
) -> int:
    database.DB_PATH = db_path
    database.initialize_database()
    network.STOP_EVENT.clear()
    worker = None

    if api_url:
        network.API_URL = api_url
        network.DEMO_MODE = False
        worker = threading.Thread(target=network.network_worker)
        worker.start()

    try:
        if not sync_only:
            collect_events(
                use_stress_dataset=use_stress_dataset,
                score_file=score_file,
            )
        if worker:
            network.STOP_EVENT.wait(wait_seconds)
    finally:
        network.STOP_EVENT.set()
        if worker:
            worker.join()

    pending = database.pending_count()
    print(f"[SQLITE] {pending} alerte(s) en attente dans {db_path}.")
    print(f"[HISTORIQUE] {database.synced_count()} alerte(s) synchronisee(s).")
    return pending


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stress",
        action="store_true",
        help="Traiter 1 000 mesures simulees en flux avec une RAM bornee.",
    )
    parser.add_argument("--db", default="greenmove.db")
    parser.add_argument("--url", default=os.environ.get("GML_API_URL"))
    parser.add_argument("--sync-only", action="store_true")
    parser.add_argument("--score-file", default="daily_score.json")
    parser.add_argument("--wait-seconds", type=float, default=5)
    args = parser.parse_args()
    run_demo(
        use_stress_dataset=args.stress,
        db_path=args.db,
        api_url=args.url,
        sync_only=args.sync_only,
        score_file=args.score_file,
        wait_seconds=args.wait_seconds,
    )
