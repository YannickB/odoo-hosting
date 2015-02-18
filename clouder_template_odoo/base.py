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

import openerp.addons.clouder.execute as execute
import erppeek

import logging
_logger = logging.getLogger(__name__)


class clouder_base_link(osv.osv):
    _inherit = 'clouder.base.link'

    def deploy_link(self, cr, uid, vals, context={}):
        super(clouder_base_link, self).deploy_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'postfix' and vals['apptype_name'] == 'odoo':
            try:
                execute.log("client = erppeek.Client('http://" + vals['server_domain'] + ":" + vals['service_options']['port']['hostport'] + "," + "db=" + vals['base_unique_name_'] + "," + "user=" + vals['apptype_admin_name'] + ", password=" + vals['base_admin_passwd'] + ")", context)
                client = erppeek.Client('http://' + vals['server_domain'] + ':' + vals['service_options']['port']['hostport'], db=vals['base_unique_name_'], user=vals['apptype_admin_name'], password=vals['base_admin_passwd'])
                execute.log("server_id = client.model('ir.model.data').get_object_reference('base', 'ir_mail_server_localhost0')[1]", context)
                server_id = client.model('ir.model.data').get_object_reference('base', 'ir_mail_server_localhost0')[1]
                execute.log("client.model('ir.mail_server').write([" + str(server_id) + "], {'name': 'postfix', 'smtp_host': 'postfix'})", context)
                client.model('ir.mail_server').write([server_id], {'name': 'postfix', 'smtp_host': 'postfix'})
            except:
                pass

            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/^mydestination =/ s/$/, ' + vals['base_fulldomain'] + '/"', '/etc/postfix/main.cf'], context)
            execute.execute(ssh, ['echo "@' + vals['base_fulldomain'] + ' ' + vals['base_unique_name_'] + '@localhost" >> /etc/postfix/virtual_aliases'], context)
            execute.execute(ssh, ['postmap', '/etc/postfix/virtual_aliases'], context)
            execute.execute(ssh, ["echo '" + vals['base_unique_name_'] + ": \"|openerp_mailgate.py --host=" + vals['server_domain'] + " --port=" + vals['service_options']['port']['hostport'] + " -u 1 -p " + vals['base_admin_passwd'] + " -d " + vals['base_unique_name_'] + "\"' >> /etc/aliases"], context)
            execute.execute(ssh, ['newaliases'], context)
            execute.execute(ssh, ['/etc/init.d/postfix', 'reload'], context)
            ssh.close()
            sftp.close()

    def purge_link(self, cr, uid, vals, context={}):
        super(clouder_base_link, self).purge_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'postfix' and vals['apptype_name'] == 'odoo':
            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/^mydestination =/ s/, ' + vals['base_fulldomain'] + '//"', '/etc/postfix/main.cf'], context)
            execute.execute(ssh, ['sed', '-i', '"/@' + vals['base_fulldomain'] + '/d"', '/etc/postfix/virtual_aliases'], context)
            execute.execute(ssh, ['postmap' , '/etc/postfix/virtual_aliases'], context)
            execute.execute(ssh, ['sed', '-i', '"/d\s' + vals['base_unique_name_'] + '/d"', '/etc/aliases'], context)
            execute.execute(ssh, ['newaliases'], context)
            execute.execute(ssh, ['/etc/init.d/postfix', 'reload'], context)
            ssh.close()
            sftp.close()