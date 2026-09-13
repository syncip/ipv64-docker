FROM python:3.10-alpine

LABEL org.opencontainers.image.title="ipv64-updater" \
      org.opencontainers.image.description="DDNS Updater fuer ipv64.net" \
      org.opencontainers.image.source="https://github.com/syncip/ipv64-docker"

ENV SCRIPT_VERSION="v0.4.0" \
    TZ=Europe/Berlin \
    INTERVAL=300 \
    PYTHONUNBUFFERED=1

WORKDIR /data

# requirements.txt zuerst kopieren -> Docker-Layer-Caching: pip install wird
# nur bei Aenderungen an requirements.txt neu ausgefuehrt, nicht bei jeder
# Aenderung an app.py/notification.py/etc.
COPY data/requirements.txt .

RUN apk add --no-cache tini tzdata \
    && pip install --no-cache-dir -r requirements.txt \
    && addgroup -S ipv64 && adduser -S -G ipv64 -h /data ipv64 \
    && mkdir -p /data/state \
    && chown -R ipv64:ipv64 /data

COPY --chown=ipv64:ipv64 data/ .
RUN chmod +x entrypoint.sh

USER ipv64

# Watchdog-Skript prueft anhand der State-Datei, ob der Update-Loop noch
# laeuft und die letzten Zyklen erfolgreich waren (siehe watchdog.py).
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python watchdog.py

ENTRYPOINT ["/sbin/tini", "--", "/data/entrypoint.sh"]
