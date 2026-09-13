#!/bin/sh
set -e

echo "██ ██████  ██    ██  ██████  ██   ██     ██    ██ ██████  ██████   █████  ████████ ███████ ██████  "
echo "██ ██   ██ ██    ██ ██       ██   ██     ██    ██ ██   ██ ██   ██ ██   ██    ██    ██      ██   ██ "
echo "██ ██████  ██    ██ ███████  ███████     ██    ██ ██████  ██   ██ ███████    ██    █████   ██████  "
echo "██ ██       ██  ██  ██    ██      ██     ██    ██ ██      ██   ██ ██   ██    ██    ██      ██   ██ "
echo "██ ██        ████    ██████       ██      ██████  ██      ██████  ██   ██    ██    ███████ ██   ██ "
echo "Version: ${SCRIPT_VERSION}"
echo ""

# exec ist wichtig: dadurch wird python zu PID des Vordergrundprozesses und
# erhaelt SIGTERM/SIGINT direkt von tini, statt dass dieses sh-Skript als
# zusaetzliche Zwischenebene das Signal erst weiterleiten muesste.
exec python -u /data/app.py
