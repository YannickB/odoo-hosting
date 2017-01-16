FROM clouder/base:3.4
MAINTAINER Yannick Buron yannick.buron@gmail.com

RUN apk add --update git

RUN git clone http://github.com/odoo/odoo.git /opt/odoo/files/odoo -b 10.0 && rm -rf /opt/odoo/files/odoo/.git
RUN mkdir /opt/odoo/files/extra

CMD tail -f /dev/null