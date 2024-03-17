#!/usr/bin/env bash

echo "██ ██████  ██    ██  ██████  ██   ██     ██    ██ ██████  ██████   █████  ████████ ███████ ██████  ";
echo "██ ██   ██ ██    ██ ██       ██   ██     ██    ██ ██   ██ ██   ██ ██   ██    ██    ██      ██   ██ ";
echo "██ ██████  ██    ██ ███████  ███████     ██    ██ ██████  ██   ██ ███████    ██    █████   ██████  ";
echo "██ ██       ██  ██  ██    ██      ██     ██    ██ ██      ██   ██ ██   ██    ██    ██      ██   ██ ";
echo "██ ██        ████    ██████       ██      ██████  ██      ██████  ██   ██    ██    ███████ ██   ██ ";
echo "Version: $SCRIPT_VERSION"
echo "                                                                                                   ";
echo "                                                                                                   ";


touch /etc/cron/crontab
echo "$CRON   python /data/app.py" >> /etc/cron/crontab
chmod 0644 /etc/cron/crontab
crontab /etc/cron/crontab

crond -f