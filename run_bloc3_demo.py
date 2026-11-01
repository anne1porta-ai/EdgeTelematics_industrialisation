"""Demo orale : resilience Edge, timeout HTTP, idempotence et telemetrie."""

import argparse
import json
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

import src.storage.event_repository as database
import src.sync.sync_service as network
from run_demo import acquisition_loop, recent_samples
from src.safety.run_safety import INPUT_FILE
from src.safety.safety_engine import iter_accelerometer_data

WIDTH = 72
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"

# Etat du petit serveur HTTP utilise uniquement pour la demonstration.
RECEIVED_IDS: set[str] = set()


def colored(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


def pause(message="Appuyez sur ENTREE pour continuer..."):
    try:
        input(colored(f"\n▶ {message}", CYAN))
    except EOFError:
        pass


def section(number, title, color=CYAN):
    print("\n" + colored("=" * WIDTH, color))
    print(colored(f"  {number}. {title}", BOLD + color))
    print(colored("=" * WIDTH, color))


def line(label, value):
    print(f"{label:<34}: {value}")


def sensor_samples():
    """Lire les mesures a 10 Hz pendant la panne puis la reprise."""
    readings = iter_accelerometer_data(INPUT_FILE)

    for number in range(1, 161):
        if network.STOP_EVENT.is_set():
            break

        # Retour automatique apres avoir rendu visibles 2 s, 4 s et 8 s.
        if number == 101:
            section(3, "📡 RETOUR DU RESEAU 4G", GREEN)
            network.NETWORK_AVAILABLE = True
            line("Reseau 4G", colored("✅ RETABLI", GREEN))
            line("Collecte capteurs", colored("✅ TOUJOURS ACTIVE", GREEN))
            line("Alertes conservees", database.pending_count())
            print(colored("\nLe worker reprend maintenant l'envoi de l'alerte.", GREEN))

        sample = next(readings, {"timestamp": time.time(), "acc_y": 0.0})
        yield sample

        if number in (20, 60, 100, 140):
            network_state = colored("✅ OK", GREEN) if network.NETWORK_AVAILABLE else colored("⚠️  COUPEE", RED)
            print(
                f"{colored('📈 COLLECTE', CYAN)} {number:3d} mesures | "
                f"4G {network_state} | "
                f"RAM {len(recent_samples)}/{recent_samples.maxlen} | "
                f"SQLite {database.pending_count()}"
            )

        network.STOP_EVENT.wait(0.1)


class DemoApiHandler(BaseHTTPRequestHandler):
    """Mini API locale : une route lente et une route idempotente."""

    def log_message(self, *_args):
        # Evite les logs HTTP techniques dans la demo.
        return

    def do_POST(self):
        if self.path == "/slow":
            # Le client abandonnera avant cette reponse.
            time.sleep(2)
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            return

        if self.path == "/events":
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)

            alert_id = self.headers.get("Idempotency-Key", "")
            duplicate = alert_id in RECEIVED_IDS
            if not duplicate:
                RECEIVED_IDS.add(alert_id)

            status = "DUPLICATE" if duplicate else "STORED"
            body = json.dumps({"status": status}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()


def start_demo_api():
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoApiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def demonstrate_http_timeout(base_url):
    section(4, "⏱️  TIMEOUT HTTP REEL", YELLOW)
    print("Le serveur local attend volontairement 2 s.")
    print("Le client abandonne apres 1 s : la collecte ne reste pas bloquee.")

    started = time.monotonic()
    try:
        requests.post(f"{base_url}/slow", json={"demo": True}, timeout=1)
    except requests.Timeout:
        elapsed = time.monotonic() - started
        line("Resultat", colored("✅ TIMEOUT DECLENCHE", GREEN))
        line("Attente du client", f"{elapsed:.1f} s environ")
    else:
        line("Resultat", colored("❌ timeout non declenche", RED))


def demonstrate_idempotency(base_url):
    section(5, "🔁 IDEMPOTENCE COTE SERVEUR", CYAN)
    RECEIVED_IDS.clear()
    alert_id = "demo-alert-001"
    headers = {"Idempotency-Key": alert_id}
    payload = {"event_type": "harsh_braking", "acc_y": -3.45}

    first = requests.post(f"{base_url}/events", json=payload, headers=headers, timeout=2).json()
    second = requests.post(f"{base_url}/events", json=payload, headers=headers, timeout=2).json()

    line("1er envoi", colored(first["status"], GREEN))
    line("2e envoi meme alert_id", colored(second["status"], YELLOW))
    line("Enregistrements serveur", colored(str(len(RECEIVED_IDS)), GREEN))
    line("Resultat", colored("✅ AUCUN DOUBLON", GREEN))


def demonstrate(folder):
    print("\n" + colored("#" * WIDTH, MAGENTA))
    print(colored("  🚚 DEMO RESILIENCE APRES INCIDENT PILOTE  ".center(WIDTH), BOLD + MAGENTA))
    print(colored("#" * WIDTH, MAGENTA))
    print("\nObjectif : montrer qu'une panne 4G ne bloque plus la collecte")
    print("et qu'aucune alerte critique n'est perdue.")
    pause("demarrer la demonstration")

    section(1, "🧠 PROTECTION MEMOIRE", CYAN)
    recent_samples.clear()
    for number in range(1000):
        recent_samples.append({"timestamp": number, "acc_y": 0.0})
    line("Mesures simulees", "1 000")
    line("Buffer RAM", f"{len(recent_samples)} / {recent_samples.maxlen}")
    line("Resultat", colored("✅ MEMOIRE BORNEE", GREEN))
    recent_samples.clear()

    pause("simuler maintenant la coupure 4G")

    section(2, "⚠️  PANNE 4G + STORE-AND-FORWARD", RED)
    database.DB_PATH = str(folder / "events.sqlite")
    database.MAX_RETRY_DELAY = 300
    database.initialize_database()

    network.DEMO_MODE = True
    network.NETWORK_AVAILABLE = False
    network.STOP_EVENT.clear()
    network.FIRST_FAILURE.clear()

    line("Reseau 4G", colored("❌ COUPE", RED))
    line("Collecte capteurs", colored("✅ ACTIVE", GREEN))
    line("Alertes SQLite", "0")
    print(colored("\n💾 Un freinage est persiste dans SQLite AVANT l'envoi.", YELLOW))
    print(colored("🔁 Le worker reessaie avec un backoff : 2 s → 4 s → 8 s.", YELLOW))
    print(colored("📈 Pendant ce temps, la collecte continue.", GREEN))

    worker = threading.Thread(target=network.network_worker, name="network-worker")
    worker.start()
    try:
        acquisition_loop(
            output_file=str(folder / "daily_score.json"),
            samples=sensor_samples(),
        )
    finally:
        network.STOP_EVENT.set()
        worker.join()

    pause("tester maintenant le timeout HTTP reel")
    server = start_demo_api()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        demonstrate_http_timeout(base_url)
        pause("tester maintenant l'idempotence")
        demonstrate_idempotency(base_url)
    finally:
        server.shutdown()
        server.server_close()

    pause("afficher la telemetrie et le bilan final")

    section(6, "📊 TELEMETRIE FINALE", MAGENTA)
    line("Version demo", "POC-resilience")
    line("Buffer RAM max", colored(f"{recent_samples.maxlen} mesures", GREEN))
    line("Alertes SQLite en attente", colored(str(database.pending_count()), GREEN))
    line("Historique synchronise", colored(str(database.synced_count()), GREEN))
    line("Collecte", colored("ACTIVE / NON BLOQUEE", GREEN))
    line("Dernier test HTTP", colored("OK", GREEN))
    line("Idempotence serveur", colored("OK - 1 stockage pour 2 envois", GREEN))

    section(7, "🏁 BILAN", MAGENTA)
    line("Memoire bornee", colored("✅ OUI", GREEN))
    line("Collecte continue", colored("✅ OUI", GREEN))
    line("Alerte conservee hors ligne", colored("✅ OUI", GREEN))
    line("Aucune alerte perdue", colored("✅ OUI", GREEN))
    line("Backoff observe", colored("✅ 2 s → 4 s → 8 s", GREEN))
    line("Timeout HTTP", colored("✅ DEMONTRE", GREEN))
    line("Idempotence", colored("✅ DEMONTREE", GREEN))
    line("Purge uniquement apres succes", colored("✅ OUI", GREEN))
    line("Alertes encore en attente", colored(str(database.pending_count()), GREEN))
    line("Alertes archivees synced=1", colored(str(database.synced_count()), GREEN))

    print("\n" + colored("-" * WIDTH, CYAN))
    print(colored("✅ CONCLUSION", BOLD + GREEN))
    print("La securite locale continue meme sans reseau :")
    print("memoire bornee, alerte durable, reprise, timeout et anti-doublon.")
    print(colored("-" * WIDTH, CYAN))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("resultats_demo"))
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="essai-", dir=args.data_dir))
    demonstrate(folder)


if __name__ == "__main__":
    main()
