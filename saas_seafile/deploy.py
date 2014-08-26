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
import erppeek

import logging
_logger = logging.getLogger(__name__)




class saas_base(osv.osv):
    _inherit = 'saas.base'

    def deploy_build(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_build(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'seafile':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            install_args = ['\n',
                     vals['base_title'] + '\n',
                     vals['base_fulldomain'] + '\n',
                     '\n','\n','\n','\n',
                     '2\n',
                     'mysql\n',
                     '\n',
                     vals['service_db_user'] + '\n',
                     vals['service_db_password'] + '\n',
                     vals['base_databases']['ccnet'] + '\n',
                     vals['base_databases']['seafile'] + '\n',
                     vals['base_databases']['seahub'] + '\n',
                     '\n']
            seahub_args = [vals['apptype_admin_email'] + '\n',
                          vals['base_admin_passwd'] + '\n',
                          vals['base_admin_passwd']]
            if not vals['base_options']['manual_install']['value']:
                #Be cautious, the install may crash because of the server name (title). Use only alphanumeric, less than 15 letter without space
                execute.execute(ssh, ['./setup-seafile-mysql.sh'],context, stdin_arg=install_args, path=vals['service_full_localpath_files'])

                execute.execute(ssh, [vals['service_full_localpath_files'] + '/seafile.sh', 'start'], context)

                execute.execute(ssh, [vals['service_full_localpath_files'] + '/seahub.sh', 'start'], context, stdin_arg=seahub_args)
            else:
                for arg in install_args:
                    execute.log(arg, context)
                for arg in seahub_args:
                    execute.log(arg, context)

            execute.execute(ssh, ['echo "[program:' + vals['base_unique_name'] + '-seafile]" >> /opt/seafile/supervisor.conf'], context)
            execute.execute(ssh, ['echo "command=su seafile -c \'' + vals['service_full_localpath_files'] + '/seafile.sh\'" >> /opt/seafile/supervisor.conf'], context)
            execute.execute(ssh, ['echo "[program:' + vals['base_unique_name'] + '-seahub]" >> /opt/seafile/supervisor.conf'], context)
            execute.execute(ssh, ['echo "command=su seafile -c \'' + vals['service_full_localpath_files'] + '/seahub.sh\'" >> /opt/seafile/supervisor.conf'], context)

            ssh.close()
            sftp.close()
        return res

class saas_save_save(osv.osv):
    _inherit = 'saas.save.save'

    #
    # def deploy_base(self, cr, uid, vals, context=None):
    #     res = super(saas_save_save, self).deploy_base(cr, uid, vals, context)
    #     context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
    #     if vals['apptype_name'] == 'drupal':
    #         ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
    #         execute.execute(ssh, ['cp', '-R', vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'], '/base-backup/' + vals['saverepo_name'] + '/site'], context)
    #         ssh.close()
    #         sftp.close()
    #     return
    #
    #
    # def restore_base(self, cr, uid, vals, context=None):
    #     res = super(saas_save_save, self).restore_base(cr, uid, vals, context)
    #     context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
    #     if vals['apptype_name'] == 'drupal':
    #         ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
    #         execute.execute(ssh, ['rm', '-rf', vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain']], context)
    #         execute.execute(ssh, ['cp', '-R', '/base-backup/' + vals['saverepo_name'] + '/site', vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain']], context)
    #         ssh.close()
    #         sftp.close()
    #     return