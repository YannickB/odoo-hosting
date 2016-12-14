FROM clouder/base:3.4
MAINTAINER Yannick Buron yannick.buron@gmail.com

# create the odoo user
RUN adduser -D -g "" odoo
RUN touch /home/odoo/.pgpass

RUN mkdir -p /opt/odoo/data
RUN mkdir -p /opt/odoo/etc
RUN mkdir -p /opt/odoo/extra-addons
RUN mkdir -p /opt/odoo/var/run
RUN mkdir -p /opt/odoo/var/log
RUN mkdir -p /opt/odoo/var/egg-cache
ADD odoo.conf /opt/odoo/etc/odoo.conf

RUN chown -R odoo:odoo /opt/odoo

CMD tail -f /dev/null