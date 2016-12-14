FROM clouder/base:3.4
MAINTAINER Yannick Buron yannick.buron@gmail.com

RUN apk add --update --no-cache nginx openssl
# nginx config
RUN sed -i -e"s/keepalive_timeout\s*65/keepalive_timeout 2/" /etc/nginx/nginx.conf
RUN echo "daemon off;" >> /etc/nginx/nginx.conf
#RUN chsh -s /bin/bash www-data
RUN mkdir /run/nginx
RUN mkdir /run/php
#RUN mkdir /var/www
#RUN chown www-data:www-data /var/www/

#RUN mkdir /run/nginx
RUN mkdir /etc/nginx/sites-available
RUN mkdir /etc/nginx/sites-enabled
RUN sed -i '/http {/a include /etc/nginx/sites-enabled/*;' /etc/nginx/nginx.conf
CMD nginx