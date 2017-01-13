FROM clouder/base:3.4
MAINTAINER Yannick Buron yannick.buron@gmail.com


# Install Postfix.
#run echo "postfix postfix/main_mailer_type string Internet site" > preseed.txt
#run echo "postfix postfix/mailname string mail.clouder.at" >> preseed.txt
# Use Mailbox format.
#run debconf-set-selections preseed.txt

RUN apk del ssmtp
RUN apk add --update supervisor postfix rsyslog

RUN echo "@edge http://dl-cdn.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories
RUN echo "@community http://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories
RUN apk add --update opendkim@community libressl2.4-libcrypto@edge libmilter@community opendkim-libs@community libressl2.4-libssl@edge

#libsasl2-2 ca-certificates libsasl2-modules supervisor opendkim opendkim-tools postfix-policyd-spf-perl spamc rsyslog

RUN sed -i '/myorigin =/d' /etc/postfix/main.cf
RUN echo "myorigin = </etc/mailname" >> /etc/postfix/main.cf
RUN touch /etc/postfix/virtual_aliases
RUN echo "virtual_alias_maps = hash:/etc/postfix/virtual_aliases" >> /etc/postfix/main.cf
RUN postmap /etc/postfix/virtual_aliases
RUN mkdir /etc/aliases-dir
#RUN mv /etc/aliases /etc/aliases-dir/aliases
RUN ln -s /etc/aliases-dir/aliases /etc/aliases

RUN echo "# DKIM" >> /etc/postfix/main.cf
RUN echo "milter_default_action = accept" >> /etc/postfix/main.cf
RUN echo "milter_protocol = 2" >> /etc/postfix/main.cf
RUN echo "smtpd_milters = inet:localhost:8891" >> /etc/postfix/main.cf
RUN echo "non_smtpd_milters = inet:localhost:8891" >> /etc/postfix/main.cf

RUN echo "smtpd_recipient_restrictions = permit_sasl_authenticated,permit_mynetworks,reject_unauth_destination,check_policy_service unix:private/policy" >> /etc/postfix/main.cf

RUN echo "policy unix - n n - - spawn user=nobody argv=/usr/sbin/postfix-policyd-spf-perl" >> /etc/postfix/master.cf

RUN mkdir -p /opt/opendkim
RUN touch /opt/opendkim/KeyTable
RUN touch /opt/opendkim/SigningTable
RUN echo "127.0.0.1" >> /opt/opendkim/TrustedHosts
RUN mkdir /etc/default
RUN echo "SOCKET='inet:8891:localhost'" >> /etc/default/opendkim
RUN echo "KeyTable           /opt/opendkim/KeyTable" >> /etc/opendkim.conf
RUN echo "SigningTable       /opt/opendkim/SigningTable" >> /etc/opendkim.conf
RUN echo "ExternalIgnoreList /opt/opendkim/TrustedHosts" >> /etc/opendkim.conf
RUN echo "InternalHosts      /opt/opendkim/TrustedHosts" >> /etc/opendkim.conf

#ADD odoo_mailgate.py /bin/odoo_mailgate.py
#RUN chmod +x /bin/odoo_mailgate.py

RUN echo "" >> /etc/supervisord.conf
RUN echo "[supervisord]" >> /etc/supervisord.conf
RUN echo "nodaemon=true" >> /etc/supervisord.conf
RUN echo "" >> /etc/supervisord.conf
RUN echo "[program:rsyslog]" >> /etc/supervisord.conf
RUN echo "command=rsyslogd" >> /etc/supervisord.conf
RUN echo "[program:postfix]" >> /etc/supervisord.conf
RUN echo "command=postfix start" >> /etc/supervisord.conf
RUN echo "autorestart=false" >> /etc/supervisord.conf
RUN echo "[program:opendkim]" >> /etc/supervisord.conf
RUN echo "command=opendkim -p inet:8891:localhost -f" >> /etc/supervisord.conf

USER root
CMD supervisord -c /etc/supervisord.conf
CMD tail -f /dev/null