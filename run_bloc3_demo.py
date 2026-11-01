"""Une alerte de freinage : collecte, stockage SQLite, puis envoi differe."""

import argparse
import tempfile
import threading
import time
from pathlib import Path

import src.storage.event_repository as database
import src.sync.sync_service as network
from run_demo import acquisition_loop, recent_samples
from src.safety.run_safety import INPUT_FILE
from src.safety.safety_engine import iter_accelerometer_data


def sensor_samples():
    """Une mesure toutes les 100 ms pendant le scenario panne puis reprise."""
    readings = iter_accelerometer_data(INPUT_FILE)

    for number in range(1, 161):
        if network.STOP_EVENT.is_set():
            break

        if number == 81:
            network.NETWORK_AVAILABLE = True
            print("\n[RESEAU] 4G retablie ; la collecte continue.")

        # Apres le CSV, le capteur simule des mesures normales, sans autre freinage.
        sample = next(readings, {"timestamp": time.time(), "acc_y": 0.0})
        yield sample

        if number == 10:
            print("[CAPTEUR] CSV lu ; poursuite avec des mesures normales simulees.")
        if number % 20 == 0:
            state = "OK" if network.NETWORK_AVAILABLE else "COUPEE"
            print(
                f"[COLLECTE] {number} mesures lues | 4G {state} | "
                f"buffer RAM {len(recent_samples)}/{recent_samples.maxlen} | "
                f"{database.pending_count()} alerte(s) en attente"
            )

        network.STOP_EVENT.wait(0.1)


def demonstrate(folder):
    print("=== DEMONSTRATION : SQLITE REEL, RESEAU SIMULE ===")

    # 1. Prouver que le buffer RAM est borne, meme avec beaucoup de mesures.
    recent_samples.clear()
    for number in range(1000):
        recent_samples.append({"timestamp": number, "acc_y": 0.0})
    print(
        f"[MEMOIRE] 1000 mesures injectees -> buffer RAM "
        f"{len(recent_samples)}/{recent_samples.maxlen} (borne)."
    )
    recent_samples.clear()

    # 2. Preparer SQLite et lancer le worker avec le reseau coupe.
    database.DB_PATH = str(folder / "events.sqlite")
    database.MAX_RETRY_DELAY = 300
    database.initialize_database()
    network.DEMO_MODE = True
    network.NETWORK_AVAILABLE = False
    network.STOP_EVENT.clear()
    network.FIRST_FAILURE.clear()
    worker = threading.Thread(target=network.network_worker)
    worker.start()

    try:
        # 3. Safety collecte dans le programme principal pendant toute la panne.
        # 4. Le worker affiche le backoff 2 s, 4 s, 8 s.
        # 5. Le scenario retablit la 4G ; le worker envoie pendant la collecte.
        acquisition_loop(
            output_file=str(folder / "daily_score.json"),
            samples=sensor_samples(),
        )
    finally:
        network.STOP_EVENT.set()
        worker.join()

    print(f"Alertes encore en attente : {database.pending_count()}")
    print(f"Resultats conserves : {folder.resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("resultats_demo"))
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    # Un dossier par essai conserve les anciennes bases.
    folder = Path(tempfile.mkdtemp(prefix="essai-", dir=args.data_dir))
    demonstrate(folder)


if __name__ == "__main__":
    main()
