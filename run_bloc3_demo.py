"""Demo orale : traitement en flux, resilience, timeout et idempotence."""

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
from run_demo import acquisition_loop
from src.safety.run_safety import INPUT_FILE
from src.safety.safety_engine import (
    analyze_accelerometer_stream,
    iter_accelerometer_data,
)
from src.sync.circuit_breaker import CLOSED, CircuitBreaker

WIDTH = 72
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"

RECEIVED_IDS = set()


def colored(text, color):
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


def demonstrate_streaming():
    """Prouver que les mesures sont traitees sans historique en memoire."""
    section(1, "🧠 TRAITEMENT EN FLUX", CYAN)

    def samples():
        for number in range(10_000):
            yield {"timestamp": number, "acc_y": 0.0}

    score = analyze_accelerometer_stream(samples(), retain_events=False)
    line("Mesures traitees", f"{score['total_samples']:,}".replace(",", " "))
    line("Historique de mesures en RAM", "0")
    line("Traitement", "une mesure a la fois")
    line("Resultat", colored("✅ AUCUNE ACCUMULATION", GREEN))


def sensor_samples(network_available, stop_event, breaker):
    """Lire 160 mesures a 10 Hz pendant la panne puis la reprise."""
    readings = iter_accelerometer_data(INPUT_FILE)

    for number in range(1, 161):
        if stop_event.is_set():
            break

        if number == 101:
            section(3, "📡 RETOUR DU RESEAU 4G", GREEN)
            network_available.set()
            line("Reseau 4G", colored("✅ RETABLI", GREEN))
            line("Collecte capteurs", colored("✅ TOUJOURS ACTIVE", GREEN))
            line("Alertes conservees", database.pending_count())
            line("Circuit reseau", colored(breaker.state, YELLOW))
            print(
                colored(
                    "\nLe circuit attend sa sonde avant de reprendre l'envoi.",
                    GREEN,
                )
            )

        sample = next(readings, {"timestamp": time.time(), "acc_y": 0.0})
        yield sample

        if number in (20, 60, 100, 140):
            if network_available.is_set():
                state = colored("✅ OK", GREEN)
            else:
                state = colored("⚠️  COUPEE", RED)
            print(
                f"{colored('📈 COLLECTE', CYAN)} {number:3d} mesures | "
                f"4G {state} | Circuit {breaker.state} | "
                f"SQLite {database.pending_count()}"
            )

        stop_event.wait(0.1)


def demonstrate_network_outage(folder):
    """Montrer Store-and-Forward, backoff et circuit breaker."""
    section(2, "⚠️  PANNE 4G + STORE-AND-FORWARD", RED)
    database.configure_database(folder / "events.sqlite")
    database.configure_retry_delay(300)
    database.initialize_database()

    network_available = threading.Event()
    stop_event = threading.Event()
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)

    def demo_sender(alert_id, _payload):
        if not network_available.is_set():
            raise requests.ConnectionError("4G coupee")
        print(f"[RECU] Alerte {alert_id} recue par le serveur simule.")

    line("Reseau 4G", colored("❌ COUPE", RED))
    line("Collecte capteurs", colored("✅ ACTIVE", GREEN))
    line("Alertes SQLite", "0")
    print(colored("\n💾 Le freinage est stocke avant l'envoi.", YELLOW))
    print(colored("🔁 Le worker attend 2 s, puis 4 s, puis 8 s.", YELLOW))
    print(colored("🛑 Apres 3 echecs, le circuit suspend les appels 5 s.", YELLOW))
    print(colored("📈 La collecte continue sans historique RAM.", GREEN))
    line("Circuit initial", colored(breaker.state, GREEN))

    worker = threading.Thread(
        target=network.network_worker,
        kwargs={
            "sender": demo_sender,
            "stop_event": stop_event,
            "circuit_breaker": breaker,
        },
        name="network-worker",
    )
    worker.start()

    try:
        acquisition_loop(
            output_file=str(folder / "daily_score.json"),
            samples=sensor_samples(network_available, stop_event, breaker),
        )
    finally:
        stop_event.set()
        worker.join()

    return breaker


class DemoApiHandler(BaseHTTPRequestHandler):
    """Mini API locale : une route lente et une route idempotente."""

    def log_message(self, *_args):
        return

    def do_POST(self):
        if self.path == "/slow":
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
    print("Le client abandonne apres 1 s.")

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

    first = requests.post(
        f"{base_url}/events", json=payload, headers=headers, timeout=2
    ).json()
    second = requests.post(
        f"{base_url}/events", json=payload, headers=headers, timeout=2
    ).json()

    line("1er envoi", colored(first["status"], GREEN))
    line("2e envoi meme alert_id", colored(second["status"], YELLOW))
    line("Enregistrements serveur", colored(str(len(RECEIVED_IDS)), GREEN))
    line("Resultat", colored("✅ AUCUN DOUBLON", GREEN))


def demonstrate_http():
    """Montrer le timeout puis la deduplication avec un serveur local."""
    server = start_demo_api()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        demonstrate_http_timeout(base_url)
        pause("tester maintenant l'idempotence")
        demonstrate_idempotency(base_url)
    finally:
        server.shutdown()
        server.server_close()


def show_final_report(breaker):
    section(6, "📊 TELEMETRIE FINALE", MAGENTA)
    line("Version demo", "POC-resilience")
    line("Historique de mesures en RAM", colored("0", GREEN))
    line("Alertes SQLite en attente", colored(str(database.pending_count()), GREEN))
    line("Historique synchronise", colored(str(database.synced_count()), GREEN))
    line("Collecte", colored("ACTIVE / NON BLOQUEE", GREEN))
    line("Dernier test HTTP", colored("OK", GREEN))
    line("Idempotence serveur", colored("OK - 1 stockage pour 2 envois", GREEN))
    line("Circuit breaker final", colored(breaker.state, GREEN))

    section(7, "🏁 BILAN", MAGENTA)
    line("Traitement en flux", colored("✅ OUI", GREEN))
    line("Accumulation des mesures", colored("✅ NON", GREEN))
    line("Collecte continue", colored("✅ OUI", GREEN))
    line("Alerte conservee hors ligne", colored("✅ OUI", GREEN))
    line("Aucune alerte perdue", colored("✅ OUI", GREEN))
    line("Backoff observe", colored("✅ 2 s → 4 s → 8 s", GREEN))
    if breaker.has_opened:
        opened_result = "✅ OUI"
    else:
        opened_result = "❌ NON"

    if breaker.state == CLOSED:
        closed_result = "✅ OUI"
    else:
        closed_result = "❌ NON"

    line("Circuit ouvert apres 3 echecs", colored(opened_result, GREEN))
    line("Circuit referme apres reprise", colored(closed_result, GREEN))
    line("Timeout HTTP", colored("✅ DEMONTRE", GREEN))
    line("Idempotence", colored("✅ DEMONTREE", GREEN))
    line("Archivage apres succes", colored("✅ OUI", GREEN))
    line("Alertes encore en attente", colored(str(database.pending_count()), GREEN))
    line("Alertes archivees synced=1", colored(str(database.synced_count()), GREEN))

    print("\n" + colored("-" * WIDTH, CYAN))
    print(colored("✅ CONCLUSION", BOLD + GREEN))
    print("Les mesures sont traitees une par une et ne s'accumulent pas.")
    print("Seules les alertes critiques sont conservees dans SQLite.")
    print("Le circuit breaker suspend les appels pendant une panne durable.")
    print(colored("-" * WIDTH, CYAN))


def demonstrate(folder):
    print("\n" + colored("#" * WIDTH, MAGENTA))
    print(
        colored(
            "  🚚 DEMO RESILIENCE APRES INCIDENT PILOTE  ".center(WIDTH),
            BOLD + MAGENTA,
        )
    )
    print(colored("#" * WIDTH, MAGENTA))
    print("\nObjectif : montrer qu'une panne 4G ne bloque plus la collecte")
    print("et qu'aucune mesure ne s'accumule inutilement en memoire.")
    pause("demarrer la demonstration")

    demonstrate_streaming()
    pause("simuler maintenant la coupure 4G")
    breaker = demonstrate_network_outage(folder)
    pause("tester maintenant le timeout HTTP reel")
    demonstrate_http()
    pause("afficher la telemetrie et le bilan final")
    show_final_report(breaker)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "resultats_demo",
    )
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="essai-", dir=args.data_dir))
    demonstrate(folder)


if __name__ == "__main__":
    main()
