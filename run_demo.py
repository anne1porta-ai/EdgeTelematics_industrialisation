"""Relier la collecte locale, SQLite et le worker réseau."""

import argparse
import os
import threading
from pathlib import Path

import src.storage.event_repository as database
import src.sync.sync_service as network
from scripts.generate_demo_data import OUTPUT_FILE as STRESS_INPUT_FILE
from scripts.generate_demo_data import SAMPLE_COUNT, generate_demo_data
from src.domain.telemetry_event import TelemetryEvent
from src.geo.run_geo import run_geo_engine
from src.safety.run_safety import INPUT_FILE, run_safety_engine
from src.storage.event_repository import save_alert

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DB = PROJECT_ROOT / "greenmove.db"
DEFAULT_SCORE = PROJECT_ROOT / "daily_score.json"


def save_braking(sample):
    """Transformer un freinage en événement métier, puis le stocker."""
    event = TelemetryEvent.harsh_braking(
        acc_y=float(sample["acc_y"]),
        timestamp=float(sample["timestamp"]),
    )
    save_alert(event)


def acquisition_loop(input_file=INPUT_FILE, output_file=DEFAULT_SCORE, samples=None):
    """Analyser les mesures une par une, sans garder tout le signal en mémoire."""
    score = run_safety_engine(
        input_file=input_file,
        output_file=output_file,
        on_event=save_braking,
        raise_on_error=True,
        samples=samples,
    )

    if score is None:
        raise RuntimeError("Le moteur Safety n'a pas produit de bilan.")

    return score


def save_zfe(point):
    """Transformer une entrée ZFE en événement métier, puis la stocker."""
    event = TelemetryEvent.zfe_entry(point)
    save_alert(event)


def collect_events(
    use_stress_dataset=False,
    score_file=DEFAULT_SCORE,
    accelerometer_file=None,
):
    """Exécuter les moteurs GEO et Safety, puis retourner leurs bilans."""
    input_file = accelerometer_file or INPUT_FILE

    if use_stress_dataset:
        generate_demo_data()
        input_file = STRESS_INPUT_FILE
        print(
            f"[STRESS] {SAMPLE_COUNT} mesures simulées seront traitées "
            "sans accumulation en RAM."
        )

    geo_result = run_geo_engine(on_event=save_zfe, raise_on_error=True)
    safety_result = acquisition_loop(input_file, score_file)

    return {
        "geo": geo_result,
        "safety": safety_result,
    }


def run_demo(
    use_stress_dataset=False,
    db_path=DEFAULT_DB,
    api_url=None,
    sync_only=False,
    score_file=DEFAULT_SCORE,
    wait_seconds=5,
):
    """Collecter localement, puis synchroniser si une API est configurée."""
    database.configure_database(db_path)
    database.initialize_database()

    network.STOP_EVENT.clear()
    worker = None

    if api_url:
        network.configure_api(api_url)
        worker = threading.Thread(
            target=network.network_worker,
            name="network-worker",
        )
        worker.start()

    try:
        if not sync_only:
            collect_events(
                use_stress_dataset=use_stress_dataset,
                score_file=score_file,
            )

        if worker is not None:
            network.STOP_EVENT.wait(wait_seconds)
    finally:
        network.STOP_EVENT.set()
        if worker is not None:
            worker.join()

    pending = database.pending_count()
    print(f"[SQLITE] {pending} alerte(s) en attente dans {db_path}.")
    print(f"[HISTORIQUE] {database.synced_count()} alerte(s) synchronisée(s).")
    return pending


def main():
    """Lire les options de la ligne de commande et lancer la démonstration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stress",
        action="store_true",
        help="Traiter 1 000 mesures simulées en flux, sans historique RAM.",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--url", default=os.environ.get("GML_API_URL"))
    parser.add_argument("--sync-only", action="store_true")
    parser.add_argument("--score-file", type=Path, default=DEFAULT_SCORE)
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


if __name__ == "__main__":
    main()
