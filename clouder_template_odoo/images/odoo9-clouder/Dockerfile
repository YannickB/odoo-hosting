FROM yannickburon/clouder:odoo9
MAINTAINER Yannick Buron yannick.buron@gmail.com

USER root
RUN apk add --update --no-cache --virtual .build-deps gcc linux-headers python-dev musl-dev libffi-dev openssl-dev \
        && pip --no-cache-dir install --upgrade paramiko erppeek apache-libcloud \
        && apk del .build-deps
USER odoo

RUN git clone http://github.com/OCA/connector.git /opt/odoo/files/extra/connector -b 9.0
RUN git clone http://github.com/clouder-community/clouder.git /opt/odoo/files/extra/clouder -b master

ENV ODOO_CONNECTOR_CHANNELS root:4
CMD /opt/odoo/files/odoo/odoo.py -c /opt/odoo/etc/odoo.conf --load=web,web_kanban,connector