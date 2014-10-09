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

import openerp.addons.saas.execute as execute

import logging
_logger = logging.getLogger(__name__)


class saas_base_link(osv.osv):
    _inherit = 'saas.base.link'

    def deploy_link(self, cr, uid, vals, context={}):
        super(saas_base_link, self).deploy_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'bind':
            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            execute.execute(ssh, ['echo "' + vals['base_name'] + ' IN CNAME ' + ('proxy' in vals['base_links'] and vals['base_links']['proxy']['target']['link_server_domain'] or vals['server_domain']) + '." >> ' + vals['domain_configfile']], context)
            if 'postfix' in vals['base_links']:
                execute.execute(ssh, ['echo "IN MX 1 ' + vals['base_links']['postfix']['target']['link_server_domain'] + '. ;' + vals['base_name'] + ' IN CNAME" >> ' + vals['domain_configfile']], context)
            execute.execute(ssh, ['/etc/init.d/bind9', 'restart'], context)
            ssh.close()
            sftp.close()

    def purge_link(self, cr, uid, vals, context={}):
        super(saas_base_link, self).purge_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'bind':
            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/' + vals['base_name'] + '\sIN\sCNAME/d"', vals['domain_configfile']], context)
            execute.execute(ssh, ['/etc/init.d/bind9', 'restart'], context)
            ssh.close()
            sftp.close()