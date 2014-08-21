# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Buron
#    Copyright 2013 Yannick Buron
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

import time
from datetime import datetime, timedelta
import subprocess
import openerp.addons.saas.execute as execute

import logging
_logger = logging.getLogger(__name__)


class saas_container(osv.osv):
    _inherit = 'saas.container'
    def deploy_post(self, cr, uid, vals, context):
        super(saas_container, self).deploy_post(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'postfix':
            ssh, sftp = execute.connect(vals['container_fullname'], context=context)
            execute.execute(ssh, ['echo "relayhost = [smtp.mandrillapp.com]" >> /etc/postfix/main.cf'], context)
            execute.execute(ssh, ['echo "smtp_sasl_auth_enable = yes" >> /etc/postfix/main.cf'], context)
            execute.execute(ssh, ['echo "smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd" >> /etc/postfix/main.cf'], context)
            execute.execute(ssh, ['echo "smtp_sasl_security_options = noanonymous" >> /etc/postfix/main.cf'], context)
            execute.execute(ssh, ['echo "smtp_use_tls = yes" >> /etc/postfix/main.cf'], context)
            execute.execute(ssh, ['echo "mynetworks = 127.0.0.0/8 172.17.0.0/16" >> /etc/postfix/main.cf'], context)
            execute.execute(ssh, ['echo "[smtp.mandrillapp.com]    ' + vals['config_mailchimp_username'] + ':' + vals['config_mailchimp_apikey'] + '" > /etc/postfix/sasl_passwd'], context)
            execute.execute(ssh, ['postmap /etc/postfix/sasl_passwd'], context)
            ssh.close()
            sftp.close()