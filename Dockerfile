FROM python:3.10-alpine

ENV TZ=Europe/Berlin
ENV CRON="*/5 * * * *"
ENV SCRIPT_VERSION="v0.3.0"
RUN mkdir -p /data
WORKDIR /data

COPY /data /data

RUN apk add --update --no-cache bash tini

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    mkdir -p /usr/local/bin/ /etc/cron/

RUN pip install --no-cache-dir -r /data/requirements.txt

RUN chmod +x entrypoint.sh
ENTRYPOINT ["/sbin/tini", "--", "/data/entrypoint.sh"]