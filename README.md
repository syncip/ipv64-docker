# ipv64 Docker Updater
Docker Updater fuer den [ipv64.net](https://ipv64.net) DDNS-Dienst.
Docker Image: [r600/ipv64-updater](https://hub.docker.com/r/r600/ipv64-updater)

## Features
- IPv4 (`A`) und IPv6 (`AAAA`) Records, auch beide gleichzeitig pro Domain
- **Mehrere Domains gleichzeitig** ueberwachen und aktualisieren
- 3 unabhaengige Dienste je IP-Familie zur Ermittlung der aktuellen IP (1 primaerer + 2 Fallback)
- **Rate-Limit-bewusst**: eigenes Soft-Limit + Mindestabstand zwischen Requests, um eine Sperre durch IPv64 zu vermeiden
- [ntfy](https://ntfy.sh)- und Discord-Benachrichtigungen bei Updates **und** bei Fehlern (Rate-Limit, nicht erreichbar, ...)
- Eingebauter **Watchdog** (Docker `HEALTHCHECK`), der erkennt, wenn der Updater haengt oder dauerhaft fehlschlaegt
- Schlanker, non-root Container ohne cron/bash (einfache Python-Dauerschleife)

## Wichtig: Aenderungen gegenueber der Vorversion (v0.3.0)
Diese Version wurde nach einem Code-Review ueberarbeitet, da der Updater in der Vorversion faktisch **nie** ein Update durchgefuehrt hat (kaputter Erreichbarkeits-Check). Neu:

- `CRON` wurde durch `INTERVAL` (Sekunden) ersetzt. `CRON="*/N * * * *"` wird beim Start automatisch grob nach Sekunden umgerechnet, sollte aber auf Dauer durch `INTERVAL` ersetzt werden.
- Der Container laeuft jetzt dauerhaft als ein einzelner Python-Prozess (keine cron/bash-Ebene mehr). Dadurch entfaellt u. a. das Risiko doppelter Cron-Eintraege nach einem Neustart und Logs landen zuverlaessig in `docker logs`.
- `ipv4.ipapi.de` wurde entfernt und durch drei etablierte Dienste je IP-Familie ersetzt (icanhazip.com, ipify.org, ident.me).
- Die Abhaengigkeit `ping3` wurde komplett entfernt (der bisherige Erreichbarkeits-Check per ICMP-Ping auf eine URL war fehlerhaft und fuehrte dazu, dass das Skript nahezu immer vorzeitig abgebrochen ist).
- Der Container laeuft jetzt als non-root User.

## docker-compose.yml
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
Ein vollstaendiges Beispiel inkl. Multi-Domain-Konfiguration findest du in [`docker-compose.yml`](./docker-compose.yml).

## Umgebungsvariablen

### Einzel-Domain
| Variable | Pflicht | Standard | Beschreibung |
|---|---|---|---|
| `DOMAIN` | ja* | - | Deine ipv64-Domain |
| `TOKEN` | ja* | - | Dein Domain- oder Account-Update-Token |
| `PREFIX` | nein | keiner | Subdomain-Prefix |
| `RECORD_TYPE` | nein | `A` | `A`, `AAAA` oder `A,AAAA` (beide gleichzeitig) |
| `CHECK_RECORD` | nein | `True` | `True` = vor dem Update pruefen, ob sich die IP geaendert hat; `False` = immer aktualisieren |

\* Entweder `DOMAIN`/`TOKEN` **oder** mindestens ein `DOMAIN_1`/`TOKEN_1`-Paar (siehe unten) muss gesetzt sein.

### Prefix direkt in der Domain angeben
`PREFIX` ist rein optional. Du kannst eine beliebig tief verschachtelte Subdomain
auch direkt komplett in `DOMAIN` eintragen - `PREFIX` einfach weglassen:

```
DOMAIN=vpn.meinserver.ipv64.net
```
```
DOMAIN=vpnhome.vpn.meinedomain.ipv64.net
```
Beides wird dann unveraendert als kompletter Hostname an ipv64 gemeldet.
Alternativ kannst du weiterhin `DOMAIN` (Basis-Domain) + `PREFIX` (auch mehrstufig,
z. B. `vpnhome.vpn`) getrennt angeben - beide Wege fuehren zum selben Ergebnis.
Nutze getrennte Felder vor allem dann, wenn du mit einem Account-Key arbeitest
und ipv64 die Subdomain dynamisch ueber den `praefix`-Parameter anlegen soll;
ansonsten ist die komplette Angabe in `DOMAIN` der unkompliziertere Weg.

### Mehrere Domains
Fuer jede zusaetzliche Domain eine durchnummerierte Variablengruppe anlegen (beliebig viele, beginnend bei `1`):

```
DOMAIN_1=erste.ipv64.net
TOKEN_1=...                 # optional, falls leer wird der globale TOKEN genutzt (z. B. Account-Key)
PREFIX_1=...                # optional
RECORD_TYPE_1=A,AAAA        # optional, Standard "A"
CHECK_RECORD_1=True         # optional, Standard "True"

DOMAIN_2=zweite.ipv64.net
PREFIX_2=vpn
...
```
`DOMAIN`/`TOKEN` (ohne Nummer) und `DOMAIN_1`, `DOMAIN_2`, ... koennen auch kombiniert werden.

### Allgemein
| Variable | Standard | Beschreibung |
|---|---|---|
| `TZ` | `Europe/Berlin` | Zeitzone fuer die Log-Zeitstempel |
| `INTERVAL` | `300` | Sekunden zwischen zwei Pruefzyklen |
| `LOG_LEVEL` | `INFO` | z. B. `DEBUG` fuer ausfuehrlichere Logs |

### Rate-Limit-Schutz
IPv64 erlaubt standardmaessig **48 Updates pro 24h** und **max. 3 Requests innerhalb von 10 Sekunden** pro Key. Der Updater schuetzt sich selbst davor:

| Variable | Standard | Beschreibung |
|---|---|---|
| `MAX_UPDATES_PER_DAY` | `40` | Eigenes Soft-Limit je Domain+Record-Typ (bewusst unter IPv64s 48, als Sicherheitspuffer). Wird das Limit erreicht, wird das Update uebersprungen statt riskiert, dass IPv64 den Key sperrt. |
| `MIN_REQUEST_INTERVAL` | `5` | Mindestabstand in Sekunden zwischen zwei API-Calls (relevant, wenn mehrere Domains denselben Token teilen). |

Antwortet die IPv64-API mit HTTP 429, wird das ebenfalls als Rate-Limit erkannt, geloggt und gemeldet (siehe Benachrichtigungen).

### Benachrichtigungen
| Variable | Standard | Beschreibung |
|---|---|---|
| `NTFY` | keiner | [ntfy.sh](https://ntfy.sh)-Topic-URL |
| `DISCORD` | keiner | Discord-Webhook-URL |
| `NOTIFY_ON_SUCCESS` | `True` | Benachrichtigung bei jedem erfolgreichen Update senden |

**Verhalten:**
- Bei einem **erfolgreichen Update** (IP hat sich geaendert): sofortige Meldung (wenn `NOTIFY_ON_SUCCESS=True`).
- Bei **unveraenderter IP**: keine Meldung (kein Spam bei jedem Zyklus).
- Bei **Fehlern** (IPv64/IP-Check nicht erreichbar, Rate-Limit erreicht, sonstiger API-Fehler): immer eine Meldung beim ersten Auftreten bzw. bei Wechsel der Fehlerart, danach als Erinnerung nur noch alle 12 Zyklen (bei Standard-Intervall ca. stuendlich), um bei dauerhaften Problemen nicht zu spammen.
- Der **Watchdog** nutzt denselben `NTFY`/`DISCORD`-Kanal fuer einen unabhaengigen Alarm, falls der Updater selbst haengt oder abstuerzt (siehe unten).

## Watchdog / Healthcheck
Der Container bringt ein `HEALTHCHECK` mit, das alle 60 Sekunden `watchdog.py` ausfuehrt. Dieses prueft:
1. Ist der letzte Update-Zyklus nicht laenger als 3 Intervalle + 60s her? (erkennt einen haengenden/abgestuerzten Prozess)
2. Gibt es fuer eine Domain 3 oder mehr aufeinanderfolgende Fehlschlaege?

Ist eine der beiden Bedingungen erfuellt, markiert Docker den Container in `docker ps` als `unhealthy` **und** es wird einmalig eine Benachrichtigung ueber `NTFY`/`DISCORD` verschickt (und erneut, sobald der Zustand sich wieder normalisiert hat). So bekommst du auch mit, wenn der Updater selbst ein Problem hat - nicht nur, wenn ein einzelnes Update fehlschlaegt.

## docker cli
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

## Lokal bauen
```bash
docker build -t ipv64-updater .
docker run --rm -e DOMAIN=test.ipv64.net -e TOKEN=xxx ipv64-updater
```
