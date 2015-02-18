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

from openerp import modules
from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

import openerp.addons.saas.execute as execute

import logging
_logger = logging.getLogger(__name__)


class saas_container_link(osv.osv):
    _inherit = 'saas.container.link'

    def deploy_link(self, cr, uid, vals, context={}):
        super(saas_container_link, self).deploy_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'shinken':
            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            file = 'container-shinken'
            if vals['container_no_save']:
                file = 'container-shinken-nosave'
            sftp.put(modules.get_module_path('saas_shinken') + '/res/' + file + '.config', vals['container_shinken_configfile'])
            execute.execute(ssh, ['sed', '-i', '"s/METHOD/' + vals['config_restore_method'] + '/g"', vals['container_shinken_configfile']], context)
            execute.execute(ssh, ['sed', '-i', '"s/TYPE/container/g"', vals['container_shinken_configfile']], context)
            execute.execute(ssh, ['sed', '-i', '"s/CONTAINER/' + vals['backup_fullname'] + '/g"', vals['container_shinken_configfile']], context)
            execute.execute(ssh, ['sed', '-i', '"s/UNIQUE_NAME/' + vals['container_fullname'] + '/g"', vals['container_shinken_configfile']], context)
            execute.execute(ssh, ['sed', '-i', '"s/HOST/' + vals['server_domain'] + '/g"', vals['container_shinken_configfile']], context)
            execute.execute(ssh, ['sed', '-i', '"s/PORT/' + str(vals['container_ports']['ssh']['hostport']) + '/g"', vals['container_shinken_configfile']], context)

            execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
            ssh.close()
            sftp.close()

    def purge_link(self, cr, uid, vals, context={}):
        super(saas_container_link, self).purge_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'shinken':
            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            execute.execute(ssh, ['rm', vals['container_shinken_configfile']], context)
            execute.execute(ssh, ['/etc/init.d/shinken', 'reload'], context)
            ssh.close()
            sftp.close()