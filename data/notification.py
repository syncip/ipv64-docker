"""
Benachrichtigungen fuer den ipv64 Updater (ntfy + Discord).

`notify()` ist der zentrale Einstiegspunkt fuer Domain-Updates:
  - Erfolgsmeldungen werden NUR verschickt, wenn tatsaechlich ein Update
    ausgefuehrt wurde (nicht bei jedem Zyklus ohne Aenderung).
  - Fehlermeldungen (unreachable / error / rate_limited) werden immer beim
    ERSTEN Auftreten bzw. bei einem Wechsel des Fehlertyps verschickt.
  - Bei dauerhaft anhaltenden Fehlern wird nicht bei jedem Zyklus erneut
    gespamt, sondern nur alle REMINDER_EVERY_N_FAILURES Zyklen als
    Erinnerung (Standard-Intervall 300s * 12 = ca. stuendlich).

`notify_watchdog()` ist ein davon unabhaengiger Kanal fuer Alarme des
Watchdogs (siehe watchdog.py), z. B. wenn der Update-Loop selbst haengt.
"""

import logging

import requests

log = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
REMINDER_EVERY_N_FAILURES = 12


def ntfy(url, message, tag=None):
    if not url or not message:
        return
    try:
        requests.post(
            url,
            data=message.encode("utf-8"),
            headers={
                "Title": "ipv64 updater",
                "Priority": "3",
                "Tags": tag or "",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        log.warning(f"ntfy-Benachrichtigung fehlgeschlagen: {exc}")


def discord(url, message):
    if not url or not message:
        return
    try:
        requests.post(
            url,
            json={"content": message, "username": "ipv64 updater"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        log.warning(f"Discord-Benachrichtigung fehlgeschlagen: {exc}")


def _dispatch(settings, message, tag):
    if not message:
        return
    ntfy(settings.get("ntfy"), message, tag)
    discord(settings.get("discord"), f":{tag}: {message}")


def notify(settings, domain_state, status, message):
    """
    status: "ok" | "error" | "rate_limited" | "unreachable"
    message: None -> es wird nichts verschickt, aber der Status/Fehlerzaehler
             im domain_state wird trotzdem aktualisiert (z. B. Reset auf 0
             Fehler nach erfolgreichem Zyklus ohne Aenderung).
    """
    prev_status = domain_state.get("status")

    if status == "ok":
        if message and settings.get("notify_on_success", True):
            _dispatch(settings, message, "green_circle")
        domain_state["status"] = "ok"
        domain_state["consecutive_failures"] = 0
        return

    domain_state["consecutive_failures"] = domain_state.get("consecutive_failures", 0) + 1
    changed = prev_status != status
    reminder_due = domain_state["consecutive_failures"] % REMINDER_EVERY_N_FAILURES == 0

    if changed or reminder_due:
        tag = "warning" if status == "rate_limited" else "red_circle"
        _dispatch(settings, message, tag)

    domain_state["status"] = status


def notify_watchdog(settings, message, healthy):
    _dispatch(settings, message, "green_circle" if healthy else "rotating_light")
