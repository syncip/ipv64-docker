# ipv64 Docker Updater
Docker Updater for [ipv64.net](https://ipv64.net) DDNS Service.  
Latest Docker Image: [here](https://hub.docker.com/r/r600/ipv64-updater)

## Features
- Ready for ipv6  
- Updates for domain prefix possible  
- IP check frequency definable with cron  
- [ntfy](https://ntfy.sh) Integration  

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
      - "RECORD_TYPE=A"
      # - "PREFIX=ddns"                      # optional
      # - "TZ=Europe/Berlin"                  # optional
      # - "CRON=*/5 * * * *"                  # optional
      # - "NTFY=https://ntfy.sh/mytopic"      # optional
```

## docker cli
```
docker run -d \
	--restart unless-stopped
	--name ipv64
	-e "DOMAIN=domain.ipv64.net" \
	-e "TOKEN=1234567890abcdefghijklmn" \
	-e "RECORD_TYPE=A" \
	-e "CRON=*/1 * * * *" \
	-e "NTFY=https://ntfy.sh/mytopic" \
	r600/ipv64-updater:latest
```