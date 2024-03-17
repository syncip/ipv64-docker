# ipv64 Docker Updater
Docker Updater for ipv64.net DDNS Service.

## Features
- Ready for ipv6  
- Updates for domain prefix possible  
- IP check frequency definable with cron  
- [ntfy](https://nty.sh) Integration  

## docker-compose.yml
```
version: "3.9"
services:
  ipv64-updater:
    image: r600/ipv64-updater:0.1
    container_name: ipv64
    restart: unless-stopped
    environment:
      - "DOMAIN=domain.ipv64.net"
      - "DOMAIN_KEY=1234567890abcdefghijklmn"
      - "RECORD_TYPE=A"
      # - "PREFIX=ddns"                      # optional
      # - "TZ=Europe/Berlin"                  # optional
      # - "CRON=*/5 * * * *"                  # optional
      # - "NTFY=https://ntfy.sh/mytopic"      # optional
```