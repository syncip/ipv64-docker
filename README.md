# ipv64 Docker Updater
Docker Updater for [ipv64.net](https://ipv64.net) DDNS Service.  
Latest Docker Image: [here](https://hub.docker.com/r/r600/ipv64-updater)

## Features
- Ready for ipv6 (your Docker network must support IPv6)  
- Updates for domains with prefix possible  
- IP check frequency definable with cron  
- [ntfy](https://ntfy.sh) notification support  
- Discord Webhook support  

## docker-compose.yml
```
version: "3.9"
services:
  ipv64-updater:
    image: r600/ipv64-updater:latest
    container_name: ipv64
    restart: unless-stopped
    environment:
      - "DOMAIN=domain.ipv64.net"
      - "TOKEN=1234567890abcdefghijklmn"
      # - "RECORD_TYPE=A"                                             # optional, standard "RECORD_TYPE=A"
      # - "PREFIX=ddns"                                               # optional, standard "PREFIX=None"
      # - "TZ=Europe/Berlin"                                          # optional, standard "TZ=Europe/Berlin"
      # - "CRON=*/5 * * * *"                                          # optional, standard "CRON=*/5 * * * *"
      # - "NTFY=https://ntfy.sh/mytopic"                              # optional, standard "NTFY=None"
      # - "DISCORD=https://discord.com/api/webhooks/121XXX"           # optional discord webhook, standard "DISCROD=None"
```

## docker cli
```
docker run -d \
	--restart unless-stopped
	--name ipv64
	-e "DOMAIN=domain.ipv64.net" \
	-e "TOKEN=1234567890abcdefghijklmn" \
	-e "RECORD_TYPE=A" \
	-e "CRON=*/5 * * * *" \
	-e "NTFY=https://ntfy.sh/mytopic" \
  -e "DISCORD=https://discord.com/api/webbhooks/XXX" \
	r600/ipv64-updater:latest
```