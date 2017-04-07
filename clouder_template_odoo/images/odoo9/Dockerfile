FROM yannickburon/clouder:odoo
MAINTAINER Yannick Buron yannick.buron@gmail.com

USER root
RUN apk add --update git
USER odoo

RUN git clone http://github.com/odoo/odoo.git /opt/odoo/files/odoo -b 9.0 && rm -rf /opt/odoo/files/odoo/.git
RUN mkdir /opt/odoo/files/extra
