FROM yannickburon/clouder:nginx
MAINTAINER Yannick Buron yannick.buron@gmail.com

RUN apk add --update supervisor \
    php7-fpm php7-json php7-zlib php7-xml php7-pdo php7-phar php7-openssl \
    php7-pdo_mysql php7-mysqli php7-session \
    php7-gd php7-iconv php7-mcrypt \
    php7-curl php7-opcache php7-ctype php7-apcu \
    php7-intl php7-bcmath php7-mbstring php7-dom php7-xmlreader mysql-client openssh-client

RUN echo "" >> /etc/supervisord.conf
RUN echo "[supervisord]" >> /etc/supervisord.conf
RUN echo "nodaemon=true" >> /etc/supervisord.conf
RUN echo "" >> /etc/supervisord.conf
RUN echo "[program:nginx]" >> /etc/supervisord.conf
RUN echo "command=nginx" >> /etc/supervisord.conf
RUN echo "[program:php]" >> /etc/supervisord.conf
RUN echo "command=php-fpm7" >> /etc/supervisord.conf

CMD supervisord -c /etc/supervisord.conf
