FROM clouder/base:3.4
MAINTAINER Yannick Buron yannick.buron@gmail.com

RUN apk add --update git

RUN git clone http://github.com/odoo/odoo.git /opt/odoo/files/odoo -b 9.0 && rm -rf /opt/odoo/files/odoo/.git
RUN mkdir /opt/odoo/files/extra

ADD http.patch /tmp/http.patch
#RUN patch /opt/odoo/files/odoo/odoo/http.py < /tmp/http.patch

CMD tail -f /dev/null