# ipv64 Docker Updater

[![Docker Pulls](https://img.shields.io/docker/pulls/r600/ipv64-updater)](https://hub.docker.com/r/r600/ipv64-updater)
[![Docker Image Size](https://img.shields.io/docker/image-size/r600/ipv64-updater/latest)](https://hub.docker.com/r/r600/ipv64-updater)
[![CI](https://github.com/syncip/ipv64-docker/actions/workflows/docker-image.yml/badge.svg)](https://github.com/syncip/ipv64-docker/actions/workflows/docker-image.yml)

Ein schlanker, non-root Docker-Container, der eine oder mehrere Domains beim
DDNS-Dienst [ipv64.net](https://ipv64.net) automatisch aktuell hält —
IPv4 (`A`) und IPv6 (`AAAA`), mit Rate-Limit-Schutz, Benachrichtigungen bei
Updates/Fehlern und eingebautem Watchdog.

**Docker Image:** [`r600/ipv64-updater`](https://hub.docker.com/r/r600/ipv64-updater) auf Docker Hub
**Unterstützte Plattformen:** `linux/amd64`, `linux/arm64`, `linux/arm/v7`, `linux/arm/v6`

---

## Inhaltsverzeichnis

- [Features](#features)
- [Schnellstart](#schnellstart)
- [Installation](#installation)
  - [docker-compose](#docker-compose)
  - [docker cli](#docker-cli)
  - [Lokal bauen](#lokal-bauen)
- [Konfiguration](#konfiguration)
  - [Einzel-Domain](#einzel-domain)
  - [Prefix direkt in der Domain](#prefix-direkt-in-der-domain)
  - [Mehrere Domains gleichzeitig](#mehrere-domains-gleichzeitig)
  - [Allgemeine Einstellungen](#allgemeine-einstellungen)
  - [Rate-Limit-Schutz](#rate-limit-schutz)
  - [Benachrichtigungen](#benachrichtigungen)
- [Anwendungsbeispiele](#anwendungsbeispiele)
- [Watchdog & Healthcheck](#watchdog--healthcheck)
- [Funktionsweise im Überblick](#funktionsweise-im-überblick)
- [Änderungen in v0.4.0 (Bugfixes)](#änderungen-in-v040-bugfixes)
- [Migration von v0.3.0](#migration-von-v030)
- [Troubleshooting / FAQ](#troubleshooting--faq)
- [Mitwirken](#mitwirken)

---

## Features

| | |
|---|---|
| 🌐 | IPv4 (`A`) und IPv6 (`AAAA`) — auch beide gleichzeitig pro Domain |
| 🧩 | **Mehrere Domains** gleichzeitig überwachen und aktualisieren |
| 🔀 | 3 unabhängige Dienste je IP-Familie zur IP-Ermittlung (1 primär + 2 Fallback) |
| 🚦 | **Rate-Limit-bewusst**: eigenes Soft-Limit + Mindestabstand zwischen Requests |
| 🔔 | [ntfy](https://ntfy.sh)- & Discord-Benachrichtigungen bei Updates **und** Fehlern |
| 🐶 | Eingebauter **Watchdog** (Docker `HEALTHCHECK`) erkennt hängende/fehlerhafte Läufe |
| 🪶 | Schlanker Container: kein `cron`/`bash`, non-root User, kleines Image |

---

## Schnellstart

```bash
docker run -d \
  --name ipv64 \
  --restart unless-stopped \
  -e "DOMAIN=deine-domain.ipv64.net" \
  -e "TOKEN=dein-update-token" \
  r600/ipv64-updater:latest
```

Das war's — der Container prüft ab sofort alle 5 Minuten die öffentliche IP
und aktualisiert bei Bedarf den DNS-Eintrag.

---

## Installation

### docker-compose

```yaml
version: "3.9"
services:
  ipv64-updater:
    image: r600/ipv64-updater:latest
    container_name: ipv64
    restart: unless-stopped
    environment:
      - "DOMAIN=domain.ipv64.net"
      - "TOKEN=1234567890abcdefghijklmn"
      # - "PREFIX=ddns"
      # - "RECORD_TYPE=A"
      # - "CHECK_RECORD=True"
      # - "TZ=Europe/Berlin"
      # - "INTERVAL=300"
      # - "MAX_UPDATES_PER_DAY=40"
      # - "MIN_REQUEST_INTERVAL=5"
      # - "NTFY=https://ntfy.sh/mytopic"
      # - "DISCORD=https://discord.com/api/webhooks/121XXX"
      # - "NOTIFY_ON_SUCCESS=True"
```

Ein vollständiges Beispiel inkl. Multi-Domain-Konfiguration liegt in
[`docker-compose.yml`](./docker-compose.yml). Starten mit:

```bash
docker compose up -d
```

### docker cli

```bash
docker run -d \
  --restart unless-stopped \
  --name ipv64 \
  -e "DOMAIN=domain.ipv64.net" \
  -e "TOKEN=1234567890abcdefghijklmn" \
  -e "RECORD_TYPE=A" \
  -e "INTERVAL=300" \
  -e "NTFY=https://ntfy.sh/mytopic" \
  -e "DISCORD=https://discord.com/api/webhooks/XXX" \
  r600/ipv64-updater:latest
```

### Lokal bauen

```bash
git clone https://github.com/syncip/ipv64-docker.git
cd ipv64-docker
docker build -t ipv64-updater .
docker run --rm -e DOMAIN=test.ipv64.net -e TOKEN=xxx ipv64-updater
```

---

## Konfiguration

### Einzel-Domain

| Variable | Pflicht | Standard | Beschreibung |
|---|:---:|---|---|
| `DOMAIN` | ✅* | – | Deine ipv64-Domain (kann auch eine komplette Subdomain sein, siehe [unten](#prefix-direkt-in-der-domain)) |
| `TOKEN` | ✅* | – | Dein Domain- oder Account-Update-Token |
| `PREFIX` | ❌ | keiner | Subdomain-Prefix, alternativ zu Punkt 1 |
| `RECORD_TYPE` | ❌ | `A` | `A`, `AAAA` oder `A,AAAA` (beide gleichzeitig aktualisieren) |
| `CHECK_RECORD` | ❌ | `True` | `True` = vor dem Update per DNS-Abfrage prüfen, ob sich die IP geändert hat; `False` = bei jedem Zyklus ungeprüft aktualisieren |

\* Entweder `DOMAIN`/`TOKEN` **oder** mindestens ein `DOMAIN_1`/`TOKEN_1`-Paar (siehe [Mehrere Domains](#mehrere-domains-gleichzeitig)) muss gesetzt sein.

### Prefix direkt in der Domain

`PREFIX` ist rein optional — du kannst eine beliebig tief verschachtelte
Subdomain auch direkt komplett in `DOMAIN` eintragen:

```bash
DOMAIN=vpn.meinserver.ipv64.net             # statt DOMAIN=meinserver.ipv64.net + PREFIX=vpn
DOMAIN=vpnhome.vpn.meinedomain.ipv64.net    # beliebig viele Ebenen möglich
```

Beide Schreibweisen führen zum selben Ergebnis. Getrennte Felder (`DOMAIN` +
`PREFIX`) sind vor allem dann sinnvoll, wenn du mit einem **Account-Key**
arbeitest und ipv64 die Subdomain dynamisch über den `praefix`-Parameter
anlegen soll. Führende/nachgestellte Punkte und Leerzeichen werden automatisch
entfernt, falls du z. B. aus einer `.env`-Datei kopierst.

### Mehrere Domains gleichzeitig

Für jede zusätzliche Domain eine durchnummerierte Variablengruppe anlegen
(beliebig viele, beginnend bei `1`):

```bash
DOMAIN_1=erste.ipv64.net
TOKEN_1=...                 # optional, sonst wird der globale TOKEN genutzt (z. B. Account-Key)
PREFIX_1=...                # optional
RECORD_TYPE_1=A,AAAA        # optional, Standard "A"
CHECK_RECORD_1=True         # optional, Standard "True"

DOMAIN_2=zweite.ipv64.net
PREFIX_2=vpn
```

`DOMAIN`/`TOKEN` (ohne Nummer) und `DOMAIN_1`, `DOMAIN_2`, … lassen sich
beliebig kombinieren — praktisch, wenn eine Domain die "Hauptkonfiguration"
ist und weitere nur ergänzend dazukommen.

### Allgemeine Einstellungen

| Variable | Standard | Beschreibung |
|---|---|---|
| `TZ` | `Europe/Berlin` | Zeitzone für die Log-Zeitstempel |
| `INTERVAL` | `300` | Sekunden zwischen zwei Prüfzyklen |
| `LOG_LEVEL` | `INFO` | z. B. `DEBUG` für ausführlichere Logs |

> Altes `CRON="*/N * * * *"`-Format wird beim Start automatisch grob nach
> Sekunden umgerechnet, sollte aber langfristig durch `INTERVAL` ersetzt
> werden (siehe [Migration](#migration-von-v030)).

### Rate-Limit-Schutz

IPv64 erlaubt standardmäßig **48 Updates pro 24h** und **max. 3 Requests
innerhalb von 10 Sekunden** pro Key. Der Updater schützt sich selbst davor:

| Variable | Standard | Beschreibung |
|---|---|---|
| `MAX_UPDATES_PER_DAY` | `40` | Eigenes Soft-Limit je Domain+Record-Typ (bewusst unter IPv64s 48 als Sicherheitspuffer). Wird es erreicht, wird das Update übersprungen statt riskiert, dass IPv64 den Key sperrt. |
| `MIN_REQUEST_INTERVAL` | `5` | Mindestabstand in Sekunden zwischen zwei API-Calls — relevant, wenn mehrere Domains denselben Token teilen. |

Antwortet die IPv64-API mit HTTP `429`, wird das ebenfalls als Rate-Limit
erkannt, geloggt und gemeldet.

### Benachrichtigungen

| Variable | Standard | Beschreibung |
|---|---|---|
| `NTFY` | keiner | [ntfy.sh](https://ntfy.sh)-Topic-URL |
| `DISCORD` | keiner | Discord-Webhook-URL |
| `NOTIFY_ON_SUCCESS` | `True` | Benachrichtigung bei jedem erfolgreichen Update senden |

**Verhalten im Detail:**

| Ereignis | Benachrichtigung? |
|---|---|
| IP hat sich geändert, Update erfolgreich | ✅ sofort (wenn `NOTIFY_ON_SUCCESS=True`) |
| IP unverändert, kein Update nötig | ❌ nie (kein Spam bei jedem Zyklus) |
| Fehler tritt **neu** auf oder ändert sich (z. B. unreachable → rate_limited) | ✅ sofort |
| Derselbe Fehler hält an | 🔁 Erinnerung nur alle 12 Zyklen (bei Standard-Intervall ca. stündlich) |
| Watchdog erkennt hängenden/abgestürzten Prozess | ✅ sofort, über denselben Kanal |

---

## Anwendungsbeispiele

**Einfachster Fall — eine Domain, IPv4:**
```bash
-e "DOMAIN=home.ipv64.net"
-e "TOKEN=abcdef123456"
```

**Dual-Stack — IPv4 und IPv6 derselben Domain:**
```bash
-e "DOMAIN=home.ipv64.net"
-e "TOKEN=abcdef123456"
-e "RECORD_TYPE=A,AAAA"
```

**Subdomain ohne separates Prefix-Feld:**
```bash
-e "DOMAIN=vpn.home.ipv64.net"
-e "TOKEN=abcdef123456"
```

**Mehrere Server/Standorte mit einem Account-Key:**
```bash
-e "TOKEN=account-key-xxxx"
-e "DOMAIN_1=standort-a.ipv64.net"
-e "DOMAIN_2=standort-b.ipv64.net"
-e "RECORD_TYPE_2=A,AAAA"
```

**Mit Benachrichtigungen bei Update & Fehlern:**
```bash
-e "DOMAIN=home.ipv64.net"
-e "TOKEN=abcdef123456"
-e "NTFY=https://ntfy.sh/mein-privates-topic"
-e "DISCORD=https://discord.com/api/webhooks/123/abc"
```

**Sehr häufige Prüfung mit engerem Rate-Limit-Puffer:**
```bash
-e "DOMAIN=home.ipv64.net"
-e "TOKEN=abcdef123456"
-e "INTERVAL=60"
-e "MAX_UPDATES_PER_DAY=30"
```

---

## Watchdog & Healthcheck

Der Container bringt ein Docker-`HEALTHCHECK` mit, das alle 60 Sekunden
`watchdog.py` ausführt und zwei Dinge prüft:

1. **Läuft der Prozess noch?** War der letzte Update-Zyklus vor mehr als
   `3 × INTERVAL + 60s`, gilt der Updater als hängengeblieben/abgestürzt.
2. **Funktioniert das Update?** Gibt es für eine Domain **3 oder mehr**
   aufeinanderfolgende Fehlschläge, wird das als anhaltendes Problem gewertet.

Trifft eine der Bedingungen zu, markiert Docker den Container in `docker ps`
als `unhealthy` **und** es wird einmalig eine Benachrichtigung über
`NTFY`/`DISCORD` verschickt (und erneut, sobald sich der Zustand wieder
normalisiert hat). So merkst du auch, wenn der Updater selbst ein Problem
hat — nicht nur, wenn ein einzelnes Update fehlschlägt.

```bash
docker inspect --format='{{json .State.Health}}' ipv64 | jq
```

---

## Funktionsweise im Überblick

```
┌────────────────────────────────────────────────────────────┐
│  app.py  (läuft dauerhaft im Vordergrund, kein cron)        │
│                                                              │
│  alle INTERVAL Sekunden, je konfigurierter Domain:          │
│    1. aktuelle öffentliche IP ermitteln                     │
│       (icanhazip → ipify → ident.me, mit Fallback)          │
│    2. optional: gesetzten DNS-Record bei ipv64 abfragen     │
│    3. bei Änderung + freiem Rate-Limit-Kontingent:           │
│       Update an ipv64.net/nic/update senden                 │
│    4. Ergebnis in state.json schreiben                      │
│    5. Benachrichtigung bei Update/Fehler                    │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
              /data/state/state.json
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│  watchdog.py  (per Docker HEALTHCHECK alle 60s)             │
│  liest state.json → prüft Alter & Fehlerzähler              │
└────────────────────────────────────────────────────────────┘
```

**Dateien im Container (`/data`):**

| Datei | Zweck |
|---|---|
| `app.py` | Haupt-Update-Loop |
| `state.py` | Konfiguration laden, State-Datei lesen/schreiben |
| `notification.py` | ntfy/Discord-Versand inkl. Spam-Schutz |
| `watchdog.py` | Healthcheck-Skript |
| `entrypoint.sh` | Minimaler Start-Wrapper (Banner + `exec python app.py`) |

---

## Änderungen in v0.4.0 (Bugfixes)

<details>
<summary><strong>Diese Version behebt 8 teils schwerwiegende Bugs aus v0.3.0 — Details aufklappen</strong></summary>

| # | Bug in v0.3.0 | Auswirkung | Behoben durch |
|---|---|---|---|
| 1 | Erreichbarkeits-Check pingte eine komplette URL (`https://ipv64.net/nic/update`) statt eines Hosts | Der Check schlug praktisch **immer** fehl → das Skript beendete sich vor jedem Update-Versuch. Der Updater hat in der Praxis **nie** ein Update durchgeführt. | Kompletter Check entfernt; Fehler werden jetzt direkt an der Stelle behandelt, an der sie auftreten (IP-Abfrage, DNS-Abfrage, API-Call) |
| 2 | Fallback-Liste der IP-Check-Dienste brach bei jedem Verbindungsfehler sofort ab (`exit()` statt nächsten Dienst zu versuchen) | Ein kurzer Ausfall eines Dienstes beendete den kompletten Zyklus, obwohl ein Fallback definiert war | Schleife geht bei Fehlern jetzt zum nächsten Dienst über; zusätzlich 3 statt 2 Dienste je IP-Familie |
| 3 | AAAA-Abfrage nutzte versehentlich die IPv4-Nameserver-Liste (Copy-&-Paste-Fehler) | Schlug in reinen IPv6-Umgebungen fehl | Korrekte IPv6-Nameserver-Liste wird jetzt für AAAA-Abfragen verwendet |
| 4 | Unbehandelte Exception bei fehlgeschlagenem Update-Request führte zu `NameError`-Absturz | Bei Netzwerkproblemen keine Fehlerbenachrichtigung, nur ein Absturz im Log | API-Call gibt jetzt immer ein strukturiertes Ergebnis zurück, nie eine unbehandelte Exception |
| 5 | `TypeError`-Absturz, wenn für eine Domain noch kein DNS-Record existierte | Neu angelegte Subdomains führten zum Absturz statt zum ersten Update | Fehlender Record wird jetzt korrekt als "muss aktualisiert werden" behandelt |
| 6 | Kaputter Shebang (`#!/usr/bin/env pytho`) | Kein Effekt im Container, aber Fehler bei direktem Aufruf | Korrigiert |
| 7 | Crontab-Datei wurde bei jedem Container-Neustart erneut angehängt statt geleert | Nach mehreren Neustarts liefen doppelte/mehrfache Update-Jobs pro Intervall → Risiko einer IPv64-Sperre | cron komplett entfernt, ersetzt durch eine einfache Python-Dauerschleife |
| 8 | Cron-Job-Output landete nicht zuverlässig in `docker logs` | Container war praktisch eine Black Box ohne Einblick in Erfolg/Fehler | Ein einziger Vordergrundprozess schreibt direkt nach `stdout` |

**Weitere Verbesserungen in v0.4.0:**
- `ping3`-Abhängigkeit vollständig entfernt (Ursache von Bug #1, benötigte zudem Raw-Socket-Rechte)
- `ipv4.ipapi.de` ersetzt durch drei etablierte, unabhängige Dienste je IP-Familie
- Mehrere Domains gleichzeitig, `RECORD_TYPE=A,AAAA` für Dual-Stack pro Domain
- Rate-Limit-Schutz (Soft-Cap + Mindestabstand + HTTP-429-Erkennung)
- Differenzierte Benachrichtigungslogik mit Spam-Schutz bei anhaltenden Fehlern
- Eingebauter Watchdog über Docker `HEALTHCHECK`
- Container läuft als non-root User, besseres Layer-Caching im Dockerfile

</details>

---

## Migration von v0.3.0

1. **`CRON` → `INTERVAL`:** `CRON="*/5 * * * *"` wird beim Start automatisch
   nach `INTERVAL=300` umgerechnet — funktioniert erstmal weiter, sollte aber
   zeitnah durch `INTERVAL=<Sekunden>` ersetzt werden.
2. Alle anderen Umgebungsvariablen (`DOMAIN`, `TOKEN`, `PREFIX`, `RECORD_TYPE`,
   `CHECK_RECORD`, `TZ`, `NTFY`, `DISCORD`) funktionieren unverändert weiter.
3. Es wird ein beschreibbares Verzeichnis `/data/state` innerhalb des
   Containers für die State-Datei genutzt. Kein Volume-Mount nötig — bei
   einer Neuerstellung des Containers (nicht bloßem Neustart) beginnt der
   Watchdog einfach wieder bei "kein Lauf bekannt" und erholt sich nach dem
   ersten Zyklus von selbst.

---

## Troubleshooting / FAQ

**Der Container zeigt `unhealthy` in `docker ps`.**
→ Logs prüfen (`docker logs ipv64`) und ggf.
`docker inspect --format='{{json .State.Health}}' ipv64` für die genaue
Watchdog-Meldung.

**Ich bekomme keine Benachrichtigung, obwohl sich meine IP geändert hat.**
→ Prüfe, ob `CHECK_RECORD` versehentlich verhindert, dass ein Unterschied
erkannt wird, und ob `NTFY`/`DISCORD` korrekt gesetzt sind. Ein Testlauf mit
`LOG_LEVEL=DEBUG` zeigt jede ermittelte IP im Log.

**Kann ich `PREFIX` mit mehreren Ebenen nutzen (z. B. `vpnhome.vpn`)?**
→ Ja, siehe [Prefix direkt in der Domain](#prefix-direkt-in-der-domain).

**Wie oft darf ich maximal aktualisieren?**
→ IPv64 erlaubt standardmäßig 48/24h. Der Updater bremst über
`MAX_UPDATES_PER_DAY` (Standard 40) von sich aus vorher ab.

---

## Mitwirken

Issues und Pull Requests sind willkommen:
[github.com/syncip/ipv64-docker](https://github.com/syncip/ipv64-docker)
