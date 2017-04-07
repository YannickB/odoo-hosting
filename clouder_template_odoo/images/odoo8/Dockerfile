FROM yannickburon/clouder:odoo
MAINTAINER Yannick Buron yannick.buron@gmail.com

USER root
RUN apk add --update git
RUN easy_install setuptools simplejson unittest2 six
USER odoo

RUN git clone http://github.com/odoo/odoo.git /opt/odoo/files/odoo -b 8.0 && rm -rf /opt/odoo/files/odoo/.git
RUN mkdir /opt/odoo/files/extra
