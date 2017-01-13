FROM clouder/base:3.4
MAINTAINER Yannick Buron yannick.buron@gmail.com

RUN apk add --update bind
RUN cp /etc/bind/named.conf.authoritative /etc/bind/named.conf

CMD named -g