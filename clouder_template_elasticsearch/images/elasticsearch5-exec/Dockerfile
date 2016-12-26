FROM clouder/base:3.4
MAINTAINER Dave Lasley <dave@laslabs.com>

# Loosely based on https://github.com/docker-library/elasticsearch/blob/master/Dockerfile.template

ENV ES_VERSION 5.0.1
ENV ES_BASE https://artifacts.elastic.co/downloads/elasticsearch

ENV GOSU_VERSION 1.10
ENV GOSU_BASE https://github.com/tianon/gosu/releases/download

ENV PACKAGES "ca-certificates curl nodejs openjdk8-jre openssl wget"

RUN apk add --update $PACKAGES

WORKDIR /tmp

# Install glibc
RUN apk --no-cache add ca-certificates openssl \
    && wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://raw.githubusercontent.com/sgerrand/alpine-pkg-glibc/master/sgerrand.rsa.pub \
    && apk --no-cache -X http://apkproxy.heroku.com/sgerrand/alpine-pkg-glibc add glibc glibc-bin

# Install Go based sudo (gosu)
RUN set -x \
    && apk add gnupg \
    && wget -O /usr/local/bin/gosu "$GOSU_BASE/$GOSU_VERSION/gosu-$(apk --print-arch |sed -e 's/x86_64/amd64/')" \
    && wget -O /usr/local/bin/gosu.asc "$GOSU_BASE/$GOSU_VERSION/gosu-$(apk --print-arch |sed -e 's/x86_64/amd64/').asc" \
    && export GNUPGHOME="$(mktemp -d)" \
    && gpg2 --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
    && gpg2 --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu \
    && rm -r "$GNUPGHOME" /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    && gosu nobody true \
    && apk del gnupg

# Install Elasticsearch
WORKDIR /opt

RUN mkdir -p /opt \
    && adduser -h /opt/elasticsearch -g elasticsearch -s /bin/bash -D elasticsearch

RUN ln -s elasticsearch elasticsearch-$ES_VERSION
USER elasticsearch
RUN set -x \
    && wget -O - "${ES_BASE}/elasticsearch-${ES_VERSION}.tar.gz" | tar -xz

ENV PATH /opt/elasticsearch/bin:$PATH

WORKDIR /opt/elasticsearch
RUN set -ex \
    && for path in \
        ./data \
        ./logs \
        ./config \
        ./config/scripts \
    ; do \
        mkdir -p "$path"; \
        chown -R elasticsearch:elasticsearch "$path"; \
    done

# Entrypoint
COPY docker-entrypoint.sh /

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["elasticsearch"]
