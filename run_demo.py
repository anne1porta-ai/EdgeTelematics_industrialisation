"""Relier la collecte existante aux fonctions SQLite des PowerPoint."""

import argparse
import os
import threading

import src.storage.event_repository as database
import src.sync.sync_service as network
from scripts.generate_demo_data import OUTPUT_FILE as STRESS_INPUT_FILE
from scripts.generate_demo_data import generate_demo_data
from src.geo.run_geo import run_geo_engine
from src.safety.run_safety import INPUT_FILE, run_safety_engine
from src.storage.event_repository import save_alert


def acquisition_loop(input_file=INPUT_FILE, output_file="daily_score.json", *, samples=None):
    """Le code Safety detecte le freinage, puis appelle directement save_alert."""
    run_safety_engine(
        input_file=input_file,
        output_file=output_file,
        on_event=save_alert,
        raise_on_error=True,
        samples=samples,
    )


def save_zfe(point):
    """Conserver aussi les evenements Geo du projet."""
    save_alert({"event_type": "zfe_entry", **point})


def collect_events(
    *, use_stress_dataset=False, score_file="daily_score.json", accelerometer_file=None
):
    input_file = accelerometer_file or INPUT_FILE
    if use_stress_dataset:
        generate_demo_data()
        input_file = str(STRESS_INPUT_FILE)
    run_geo_engine(on_event=save_zfe, raise_on_error=True)
    acquisition_loop(input_file, score_file)


def run_demo(
    use_stress_dataset=False,
    *,
    db_path="greenmove.db",
    api_url=None,
    sync_only=False,
    score_file="daily_score.json",
    wait_seconds=5,
):
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
            collect_events(use_stress_dataset=use_stress_dataset, score_file=score_file)
        if worker:
            network.STOP_EVENT.wait(wait_seconds)
    finally:
        network.STOP_EVENT.set()
        if worker:
            worker.join()

    pending = database.pending_count()
    print(f"[SQLITE] {pending} alerte(s) en attente dans {db_path}.")
    return pending


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stress", action="store_true")
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
