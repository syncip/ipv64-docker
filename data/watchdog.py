#!/usr/bin/env python3
"""
Watchdog fuer den ipv64 Updater.

Wird von Dockers HEALTHCHECK periodisch aufgerufen (siehe Dockerfile) und
prueft anhand der State-Datei von app.py, ob:

  1. der Update-Loop ueberhaupt noch laeuft (State-Datei aktuell genug -
     erkennt einen haengenden oder abgestuerzten Prozess), und
  2. die letzten Durchlaeufe nicht dauerhaft fuer eine Domain fehlschlagen.

Exit-Code 0 = gesund, 1 = ungesund (Docker markiert den Container dann in
`docker ps` als "unhealthy"). Zusaetzlich wird bei einem Wechsel des
Gesundheitszustands (gesund <-> ungesund) einmalig eine eigene
Benachrichtigung verschickt - unabhaengig von den Update-Benachrichtigungen
in app.py, damit ein haengender Updater nicht unbemerkt bleibt.
"""

import logging
import sys
import time

import notification
import state as state_module

logging.basicConfig(
    format="%(asctime)s - WATCHDOG - %(levelname)s - %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
    level="INFO",
)
log = logging.getLogger("watchdog")

# Ab so vielen aufeinanderfolgenden Fehlern fuer eine einzelne Domain wird
# der Gesamtzustand als "ungesund" gewertet.
FAILURE_ALERT_THRESHOLD = 3

# Zusaetzlicher Sicherheitspuffer (Sekunden) oben auf "3 verpasste Zyklen",
# um kurze Verzoegerungen nicht sofort als Ausfall zu werten.
GRACE_PERIOD_SECONDS = 60


def main():
    settings = state_module.load_settings()
    current_state = state_module.read_state()

    max_age = settings["interval"] * 3 + GRACE_PERIOD_SECONDS

    healthy = True
    problems = []

    last_run_iso = current_state.get("last_run")
    if not last_run_iso:
        healthy = False
        problems.append("Es wurde noch kein abgeschlossener Update-Zyklus protokolliert.")
    else:
        try:
            age = time.time() - state_module.iso_to_timestamp(last_run_iso)
        except ValueError:
            healthy = False
            age = None
            problems.append(f"Zeitstempel des letzten Laufs ist ungueltig: {last_run_iso!r}")

        if age is not None and age > max_age:
            healthy = False
            problems.append(
                f"Letzter Durchlauf ist {int(age)}s her (erlaubt: {max_age}s) - "
                f"der Update-Loop scheint haengen geblieben oder abgestuerzt zu sein."
            )

    for key, domain_state in current_state.get("domains", {}).items():
        failures = domain_state.get("consecutive_failures", 0)
        if failures >= FAILURE_ALERT_THRESHOLD:
            healthy = False
            problems.append(f"{key}: {failures} aufeinanderfolgende Fehler (Status: {domain_state.get('status')}).")

    was_healthy = current_state.get("watchdog_healthy", True)

    if healthy != was_healthy:
        if healthy:
            notification.notify_watchdog(settings, "Watchdog: ipv64-updater laeuft wieder normal.", healthy=True)
        else:
            notification.notify_watchdog(
                settings,
                "Watchdog: Problem mit ipv64-updater erkannt:\n- " + "\n- ".join(problems),
                healthy=False,
            )
        current_state["watchdog_healthy"] = healthy
        state_module.write_state(current_state)

    if healthy:
        log.info("Status: OK")
        sys.exit(0)

    for problem in problems:
        log.warning(problem)
    sys.exit(1)


if __name__ == "__main__":
    main()
