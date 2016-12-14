FROM clouder/base:3.4
MAINTAINER Yannick Buron yannick.buron@gmail.com

RUN touch /tmp/odoo-ssh
RUN apk add --update openssh
RUN mkdir /var/run/sshd
RUN chmod 0755 /var/run/sshd
USER root

CMD /usr/sbin/sshd -ddd