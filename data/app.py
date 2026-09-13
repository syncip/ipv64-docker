#!/usr/bin/env python3
"""
ipv64 DDNS Updater

Aktualisiert einen oder mehrere DNS-Records bei ipv64.net und ist sich
dabei der Rate-Limits von IPv64 bewusst (Default: 48 Updates/24h,
max. 3 Requests/10s pro Key).

Laeuft als Dauerschleife im Vordergrund (kein cron mehr noetig) und
schreibt nach jedem Zyklus eine State-Datei, die vom Watchdog
(watchdog.py) fuer den Docker HEALTHCHECK ausgewertet wird.
"""

import logging
import os
import signal
import sys
import time

import dns.resolver
import requests

import notification
import state as state_module

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    stream=sys.stdout,
)
log = logging.getLogger("ipv64-updater")

IPV64_API_URL = "https://ipv64.net/nic/update"
IPV64_NAMESERVERS_IPV4 = ["159.69.110.93", "167.235.231.182"]
IPV64_NAMESERVERS_IPV6 = ["2a01:4f8:1c1e:a6a8::1", "2a01:4f8:c010:b4fc::1"]

# Je Record-Typ mehrere unabhaengige Dienste zur Ermittlung der aktuellen
# oeffentlichen IP (1 primaerer + 2 Fallback-Dienste).
IP_CHECK_SERVICES = {
    "A": [
        "https://ipv4.icanhazip.com",
        "https://api.ipify.org",
        "https://v4.ident.me",
    ],
    "AAAA": [
        "https://ipv6.icanhazip.com",
        "https://api6.ipify.org",
        "https://v6.ident.me",
    ],
}

REQUEST_TIMEOUT = 10
DAY_IN_SECONDS = 86400
MAX_STORED_TIMESTAMPS = 200  # verhindert unbegrenztes Wachstum der State-Datei

_shutdown_requested = False
_last_api_call_monotonic = 0.0


def _handle_shutdown(signum, _frame):
    global _shutdown_requested
    log.info(f"Signal {signum} erhalten, beende nach aktuellem Zyklus...")
    _shutdown_requested = True


def get_current_ip(record_type, headers):
    """Ermittelt die aktuelle oeffentliche IP ueber mehrere Dienste.

    Anders als im Original wird bei einem Netzwerkfehler zum naechsten
    Dienst in der Liste weitergegangen (statt das ganze Script zu
    beenden)."""
    for url in IP_CHECK_SERVICES.get(record_type, []):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            log.warning(f"IP-Check-Dienst {url} nicht erreichbar ({exc}). Versuche naechsten Dienst.")
            continue

        ip = response.text.strip()
        if ip:
            log.debug(f"Aktuelle IP ({record_type}) via {url}: {ip}")
            return ip

        log.warning(f"IP-Check-Dienst {url} lieferte eine leere Antwort. Versuche naechsten Dienst.")

    return None


def get_dns_record(domain, prefix, record_type):
    """Fragt den aktuell gesetzten DNS-Record direkt bei den IPv64
    Nameservern ab. Nutzt fuer AAAA-Abfragen jetzt korrekt die IPv6-
    Nameserver (Bugfix gegenueber dem Original)."""
    fqdn = f"{prefix}.{domain}" if prefix else domain
    nameservers = IPV64_NAMESERVERS_IPV4 if record_type == "A" else IPV64_NAMESERVERS_IPV6

    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = nameservers
    resolver.timeout = REQUEST_TIMEOUT
    resolver.lifetime = REQUEST_TIMEOUT

    try:
        answer = resolver.resolve(fqdn, record_type, raise_on_no_answer=False)
    except Exception as exc:  # dnspython wirft diverse Exception-Typen
        log.warning(f"DNS-Abfrage fuer {fqdn} ({record_type}) fehlgeschlagen: {exc}")
        return None

    if answer is None:
        # Kein Record vorhanden (z. B. neue Domain) - das ist kein Fehler,
        # sondern bedeutet nur "es muss auf jeden Fall aktualisiert werden".
        log.info(f"Fuer {fqdn} ({record_type}) ist noch kein DNS-Record gesetzt.")
        return []

    return [rdata.to_text() for rdata in answer]


def _respect_rate_limit(min_interval):
    """Sorgt fuer einen Mindestabstand zwischen zwei IPv64-API-Calls,
    um das Limit von max. 3 Requests/10s pro Key nicht zu reissen -
    relevant vor allem, wenn mehrere Domains denselben Token nutzen."""
    global _last_api_call_monotonic
    now = time.monotonic()
    wait_for = min_interval - (now - _last_api_call_monotonic)
    if wait_for > 0:
        time.sleep(wait_for)
    _last_api_call_monotonic = time.monotonic()


def call_ipv64_update(token, domain, prefix, ip, headers, min_interval):
    """Ruft die IPv64 Update-API auf.

    Gibt IMMER ein Ergebnis-Dict zurueck statt (wie im Original) bei einem
    fehlgeschlagenen Request eine unbehandelte Exception zu werfen."""
    _respect_rate_limit(min_interval)

    params = {"key": token, "domain": domain, "ip": ip}
    if prefix:
        params["praefix"] = prefix

    try:
        response = requests.post(IPV64_API_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return {"status": "unreachable", "detail": str(exc)}

    if response.status_code == 429:
        return {"status": "rate_limited", "detail": response.text.strip()[:200]}
    if response.status_code >= 400:
        return {"status": "error", "detail": f"HTTP {response.status_code}: {response.text.strip()[:200]}"}

    return {"status": "ok", "detail": response.text.strip()[:200]}


def _count_recent_updates(timestamps, window_seconds=DAY_IN_SECONDS):
    cutoff = time.time() - window_seconds
    return len([t for t in timestamps if t > cutoff])


def process_domain(cfg, settings, headers, current_state):
    """Prueft/aktualisiert alle konfigurierten Record-Typen einer Domain."""
    for record_type in cfg["record_types"]:
        key = state_module.domain_key(cfg["domain"], cfg["prefix"], record_type)
        domain_state = current_state["domains"].setdefault(key, {"update_timestamps": []})
        domain_state.setdefault("update_timestamps", [])

        display_name = f"{(cfg['prefix'] + '.') if cfg['prefix'] else ''}{cfg['domain']} ({record_type})"

        if record_type not in ("A", "AAAA"):
            log.warning(f"Unbekannter RECORD_TYPE '{record_type}' fuer {display_name}, ueberspringe.")
            continue

        if not cfg["token"]:
            log.warning(f"Kein TOKEN fuer {display_name} konfiguriert, ueberspringe.")
            continue

        current_ip = get_current_ip(record_type, headers)
        if current_ip is None:
            log.warning(f"{display_name}: Konnte aktuelle IP nicht ermitteln (alle Dienste nicht erreichbar).")
            notification.notify(settings, domain_state, "unreachable",
                                 f"{display_name}: Keiner der IP-Check-Dienste ist erreichbar.")
            continue

        if cfg["check_record"]:
            set_ips = get_dns_record(cfg["domain"], cfg["prefix"], record_type)
            if set_ips is None:
                notification.notify(settings, domain_state, "unreachable",
                                     f"{display_name}: DNS-Abfrage bei den IPv64-Nameservern fehlgeschlagen.")
                continue
        else:
            set_ips = []

        if current_ip in set_ips:
            log.info(f"{display_name}: Kein Update noetig (IP unveraendert: {current_ip}).")
            notification.notify(settings, domain_state, "ok", None)
            continue

        # Eigenes Soft-Limit pruefen, BEVOR die IPv64-API belastet wird.
        recent_updates = _count_recent_updates(domain_state["update_timestamps"])
        if recent_updates >= settings["max_updates_per_day"]:
            log.warning(
                f"{display_name}: Eigenes Limit von {settings['max_updates_per_day']} Updates/24h "
                f"erreicht ({recent_updates} in den letzten 24h). Update wird uebersprungen."
            )
            notification.notify(
                settings, domain_state, "rate_limited",
                f"{display_name}: Eigenes Update-Limit ({settings['max_updates_per_day']}/24h) erreicht - "
                f"Update wird uebersprungen, um eine Sperre durch IPv64 zu vermeiden.",
            )
            continue

        result = call_ipv64_update(cfg["token"], cfg["domain"], cfg["prefix"], current_ip, headers,
                                    settings["min_request_interval"])

        if result["status"] == "ok":
            domain_state["update_timestamps"].append(time.time())
            domain_state["update_timestamps"] = domain_state["update_timestamps"][-MAX_STORED_TIMESTAMPS:]
            log.info(f"{display_name}: Update erfolgreich (alt: {set_ips or 'unbekannt'}, neu: {current_ip}).")
            notification.notify(
                settings, domain_state, "ok",
                f"{display_name}: Update erfolgreich (alt: {set_ips or 'unbekannt'}, neu: {current_ip}).",
            )
        elif result["status"] == "rate_limited":
            log.warning(f"{display_name}: IPv64 meldet Rate-Limit ({result['detail']}).")
            notification.notify(
                settings, domain_state, "rate_limited",
                f"{display_name}: IPv64 hat das Update mit einem Rate-Limit-Fehler abgelehnt: {result['detail']}",
            )
        elif result["status"] == "unreachable":
            log.warning(f"{display_name}: IPv64-API nicht erreichbar ({result['detail']}).")
            notification.notify(
                settings, domain_state, "unreachable",
                f"{display_name}: IPv64-API nicht erreichbar: {result['detail']}",
            )
        else:
            log.warning(f"{display_name}: Update fehlgeschlagen ({result['detail']}).")
            notification.notify(
                settings, domain_state, "error",
                f"{display_name}: Update fehlgeschlagen: {result['detail']}",
            )


def run_cycle(configs, settings):
    headers = {"User-Agent": f"ipv64-updater/{settings['script_version']}"}
    current_state = state_module.read_state()

    for cfg in configs:
        process_domain(cfg, settings, headers, current_state)

    current_state["last_run"] = state_module.utcnow_iso()
    state_module.write_state(current_state)


def _apply_timezone():
    tz = os.environ.get("TZ")
    if not tz:
        return
    os.environ["TZ"] = tz
    try:
        time.tzset()
    except AttributeError:
        pass  # time.tzset() gibt es nur auf Unix - im Container immer verfuegbar


def main():
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    _apply_timezone()

    settings = state_module.load_settings()
    configs = state_module.load_domain_configs()

    if not configs:
        log.error(
            "Keine Domain konfiguriert. Setze mindestens DOMAIN und TOKEN "
            "(oder DOMAIN_1/TOKEN_1, DOMAIN_2/TOKEN_2, ...). Beende."
        )
        sys.exit(1)

    domain_list = ", ".join(c["domain"] for c in configs)
    log.info(
        f"ipv64-updater {settings['script_version']} gestartet. "
        f"{len(configs)} Domain(s) konfiguriert ({domain_list}), Intervall: {settings['interval']}s."
    )

    while not _shutdown_requested:
        try:
            run_cycle(configs, settings)
        except Exception:
            log.exception("Unerwarteter Fehler im Update-Zyklus, wird im naechsten Intervall erneut versucht.")

        for _ in range(settings["interval"]):
            if _shutdown_requested:
                break
            time.sleep(1)

    log.info("Beendet.")


if __name__ == "__main__":
    main()
