"""
Zentrale Konfigurations- und State-Verwaltung fuer den ipv64 Updater.

Wird sowohl vom Haupt-Update-Loop (app.py) als auch vom Watchdog
(watchdog.py) genutzt, damit beide exakt dieselbe Sicht auf die
Konfiguration und den zuletzt bekannten Zustand haben.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone

STATE_DIR = os.environ.get("STATE_DIR", "/data/state")
STATE_FILE = os.path.join(STATE_DIR, "state.json")

log = logging.getLogger(__name__)


def bool_env(value, default=True):
    """Robustere Bool-Auswertung als beim Original (case-insensitiv,
    akzeptiert true/false/1/0/yes/no)."""
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Globale Einstellungen
# ---------------------------------------------------------------------------

def load_settings():
    return {
        "script_version": os.environ.get("SCRIPT_VERSION", "dev"),
        "interval": _load_interval(),
        "ntfy": os.environ.get("NTFY") or None,
        "discord": os.environ.get("DISCORD") or None,
        "notify_on_success": bool_env(os.environ.get("NOTIFY_ON_SUCCESS"), default=True),
        "max_updates_per_day": _load_int("MAX_UPDATES_PER_DAY", 40),
        "min_request_interval": _load_float("MIN_REQUEST_INTERVAL", 5.0),
    }


def _load_int(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        log.warning(f"{name}='{raw}' ist ungueltig, nutze Standard ({default}).")
        return default


def _load_float(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        log.warning(f"{name}='{raw}' ist ungueltig, nutze Standard ({default}).")
        return default


def _load_interval():
    """
    Neues, einfaches Intervall in Sekunden (INTERVAL).
    Alt-Kompatibilitaet: ein gesetztes CRON="*/N * * * *" wird grob in
    Sekunden umgerechnet, falls kein INTERVAL gesetzt ist.
    """
    raw_interval = os.environ.get("INTERVAL")
    if raw_interval:
        try:
            value = int(raw_interval)
            if value > 0:
                return value
        except ValueError:
            pass
        log.warning(f"INTERVAL='{raw_interval}' ist ungueltig, nutze Standard (300s).")
        return 300

    cron = os.environ.get("CRON")
    if cron:
        match = re.match(r"^\*/(\d+)\s+\*\s+\*\s+\*\s+\*$", cron.strip())
        if match:
            minutes = int(match.group(1))
            if minutes > 0:
                log.info(f"CRON='{cron}' erkannt, nutze INTERVAL={minutes * 60}s (Alt-Kompatibilitaet).")
                return minutes * 60
        log.warning(
            f"CRON='{cron}' konnte nicht automatisch umgerechnet werden. "
            f"Bitte auf INTERVAL=<Sekunden> umstellen. Nutze Standard (300s)."
        )

    return 300


# ---------------------------------------------------------------------------
# Domain-Konfiguration (Einzel- & Multi-Domain)
# ---------------------------------------------------------------------------

def load_domain_configs():
    """
    Laedt eine oder mehrere Domain-Konfigurationen aus den Environment
    Variablen.

    Unterstuetzt:
      - Einzel-Domain (Altformat, weiterhin unterstuetzt):
            DOMAIN, TOKEN, PREFIX, RECORD_TYPE, CHECK_RECORD
      - Mehrere Domains (neu), beliebig viele, durchnummeriert ab 1:
            DOMAIN_1, TOKEN_1, PREFIX_1, RECORD_TYPE_1, CHECK_RECORD_1
            DOMAIN_2, TOKEN_2, ...
      Ein globaler TOKEN/RECORD_TYPE/CHECK_RECORD dient dabei als Fallback
      fuer nummerierte Eintraege, bei denen kein eigener Wert gesetzt ist
      (z. B. wenn ein IPv64-Account-Key fuer mehrere Domains verwendet wird).
    """
    configs = []

    base_token = os.environ.get("TOKEN")
    base_record_type = os.environ.get("RECORD_TYPE", "A")
    base_check_record = os.environ.get("CHECK_RECORD")

    if os.environ.get("DOMAIN"):
        configs.append(_build_domain_config(
            domain=os.environ["DOMAIN"],
            token=base_token,
            prefix=os.environ.get("PREFIX"),
            record_type=base_record_type,
            check_record=base_check_record,
        ))

    index = 1
    while True:
        domain = os.environ.get(f"DOMAIN_{index}")
        if not domain:
            break
        configs.append(_build_domain_config(
            domain=domain,
            token=os.environ.get(f"TOKEN_{index}") or base_token,
            prefix=os.environ.get(f"PREFIX_{index}"),
            record_type=os.environ.get(f"RECORD_TYPE_{index}", base_record_type),
            check_record=os.environ.get(f"CHECK_RECORD_{index}", base_check_record),
        ))
        index += 1

    return configs


def _build_domain_config(domain, token, prefix, record_type, check_record):
    record_types = [rt.strip().upper() for rt in (record_type or "A").split(",") if rt.strip()]
    return {
        "domain": domain,
        "token": token,
        "prefix": prefix or None,
        "record_types": record_types or ["A"],
        "check_record": bool_env(check_record, default=True),
    }


# ---------------------------------------------------------------------------
# State-Datei (persistiert Zeitstempel/Status je Domain+Record, wird vom
# Watchdog gelesen um zu erkennen, ob der Updater noch laeuft/funktioniert)
# ---------------------------------------------------------------------------

def _ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def read_state():
    _ensure_state_dir()
    if not os.path.isfile(STATE_FILE):
        return {"domains": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("domains", {})
            return data
    except (json.JSONDecodeError, OSError) as exc:
        log.warning(f"Konnte State-Datei nicht lesen ({exc}). Starte mit leerem State.")
        return {"domains": {}}


def write_state(current_state):
    _ensure_state_dir()
    tmp_path = STATE_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(current_state, f, indent=2)
    os.replace(tmp_path, STATE_FILE)


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def iso_to_timestamp(iso_string):
    return datetime.fromisoformat(iso_string).timestamp()


def domain_key(domain, prefix, record_type):
    return f"{domain}|{prefix or ''}|{record_type}"
