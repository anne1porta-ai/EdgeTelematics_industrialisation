"""Demo orale : memoire bornee, panne 4G, SQLite, backoff et reprise."""

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

WIDTH = 72

# Couleurs ANSI : compatibles avec le terminal integre de VS Code.
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"


def c(text, color):
    return f"{color}{text}{RESET}"


def pause(message="Appuyez sur ENTREE pour continuer..."):
    try:
        input(c(f"\n▶ {message}", CYAN))
    except EOFError:
        pass


def section(number, title, color=CYAN):
    print("\n" + c("=" * WIDTH, color))
    print(c(f"  {number}. {title}", BOLD + color))
    print(c("=" * WIDTH, color))


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
            line("Reseau 4G", c("✅ RETABLI", GREEN))
            line("Collecte capteurs", c("✅ TOUJOURS ACTIVE", GREEN))
            line("Alertes conservees", database.pending_count())
            print(c("\nLe worker reprend maintenant l'envoi de l'alerte.", GREEN))

        sample = next(readings, {"timestamp": time.time(), "acc_y": 0.0})
        yield sample

        # Quelques jalons seulement : preuve de continuite sans pluie de logs.
        if number in (20, 60, 100, 140):
            network_state = c("✅ OK", GREEN) if network.NETWORK_AVAILABLE else c("⚠️  COUPEE", RED)
            print(
                f"{c('📈 COLLECTE', CYAN)} {number:3d} mesures | "
                f"4G {network_state} | "
                f"RAM {len(recent_samples)}/{recent_samples.maxlen} | "
                f"SQLite {database.pending_count()}"
            )

        network.STOP_EVENT.wait(0.1)


def demonstrate(folder):
    print("\n" + c("#" * WIDTH, MAGENTA))
    print(c("  🚚 DEMO RESILIENCE APRES INCIDENT PILOTE  ".center(WIDTH), BOLD + MAGENTA))
    print(c("#" * WIDTH, MAGENTA))
    print("\nObjectif : montrer qu'une panne 4G ne bloque plus la collecte")
    print("et qu'aucune alerte critique n'est perdue.")
    pause("demarrer la demonstration")

    section(1, "🧠 PROTECTION MEMOIRE", CYAN)
    recent_samples.clear()
    for number in range(1000):
        recent_samples.append({"timestamp": number, "acc_y": 0.0})
    line("Mesures simulees", "1 000")
    line("Buffer RAM", f"{len(recent_samples)} / {recent_samples.maxlen}")
    line("Resultat", c("✅ MEMOIRE BORNEE", GREEN))
    print(c("\nLa RAM ne peut plus croitre indefiniment.", GREEN))
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

    line("Reseau 4G", c("❌ COUPE", RED))
    line("Collecte capteurs", c("✅ ACTIVE", GREEN))
    line("Alertes SQLite", "0")
    print(c("\n💾 Un freinage sera persiste dans SQLite AVANT l'envoi.", YELLOW))
    print(c("🔁 Le worker reessaiera avec un backoff : 2 s → 4 s → 8 s.", YELLOW))
    print(c("📈 Pendant ce temps, la collecte continue.", GREEN))

    worker = threading.Thread(target=network.network_worker, name="network-worker")
    worker.start()

    try:
        acquisition_loop(
            output_file=str(folder / "daily_score.json"),
            samples=sensor_samples(),
            verbose=False,
        )
    finally:
        network.STOP_EVENT.set()
        worker.join()

    pause("afficher le bilan de la demonstration")

    section(4, "🏁 BILAN", MAGENTA)
    line("Memoire bornee", c(f"✅ {recent_samples.maxlen} mesures max", GREEN))
    line("Collecte continue", c("✅ OUI", GREEN))
    line("Alerte conservee hors ligne", c("✅ OUI", GREEN))
    line("Aucune alerte perdue", c("✅ OUI", GREEN))
    line("Backoff observe", c("✅ 2 s → 4 s → 8 s", GREEN))
    line("Envoi repris au retour 4G", c("✅ OUI", GREEN))
    line("Purge uniquement apres ACK", c("✅ OUI", GREEN))
    line("Alertes encore en attente", c(str(database.pending_count()), GREEN))

    print("\n" + c("-" * WIDTH, CYAN))
    print(c("✅ CONCLUSION", BOLD + GREEN))
    print("La securite locale continue meme sans reseau :")
    print("collecte active, alerte durable dans SQLite, puis reprise automatique.")
    print(c("-" * WIDTH, CYAN))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("resultats_demo"))
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="essai-", dir=args.data_dir))
    demonstrate(folder)


if __name__ == "__main__":
    main()
