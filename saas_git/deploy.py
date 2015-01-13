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

class saas_service(osv.osv):
    _inherit = 'saas.service'

    def deploy_post_service(self, cr, uid, vals, context):
        super(saas_service, self).deploy_post_service(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['app_code'] == 'gitlab':
            ssh, sftp = execute.connect(vals['container_fullname'], username='root', context=context)
            execute.execute(ssh, ['cp', vals['service_full_localpath_files'] + '/config/gitlab.yml.example', vals['service_full_localpath_files'] + '/config/gitlab.yml'], context)
            execute.execute(ssh, ['chown', '-R', 'git', vals['service_full_localpath_files'] + '/log'], context)
            execute.execute(ssh, ['chown', '-R', 'git', vals['service_full_localpath_files'] + '/tmp'], context)
            execute.execute(ssh, ['chmod', '-R', 'u+rwX,go-w', vals['service_full_localpath_files'] + '/log'], context)
            execute.execute(ssh, ['chmod', '-R', 'u+rwX,go-w', vals['service_full_localpath_files'] + '/tmp'], context)

            execute.execute(ssh, ['mkdir', vals['service_full_localpath'] + '/gitlab-satellites'], context)
            execute.execute(ssh, ['chmod', '-R', 'u+rwx,g=rx,o-rwx', vals['service_full_localpath'] + '/gitlab-satellites'], context)

            execute.execute(ssh, ['chmod', '-R', 'u+rwX', vals['service_full_localpath_files'] + '/tmp/pids'], context)
            execute.execute(ssh, ['chmod', '-R', 'u+rwX', vals['service_full_localpath_files'] + '/tmp/sockets'], context)
            execute.execute(ssh, ['chmod', '-R', 'u+rwX', vals['service_full_localpath_files'] + '/public/uploads'], context)

            execute.execute(ssh, ['cp', vals['service_full_localpath_files'] + '/config/unicorn.rb.example', vals['service_full_localpath_files'] + '/config/unicorn.rb'], context)
            execute.execute(ssh, ['cp', vals['service_full_localpath_files'] + '/config/initializers/rack_attack.rb.example', vals['service_full_localpath_files'] + '/config/initializers/rack_attack.rb'], context)
            execute.execute(ssh, ['cp', vals['service_full_localpath_files'] + '/config/resque.yml.example', vals['service_full_localpath_files'] + '/config/resque.yml'], context)
            execute.execute(ssh, ['chown', '-R', 'git', vals['service_full_localpath']], context)
            ssh.close()
            sftp.close()

        return


class saas_base(osv.osv):
    _inherit = 'saas.base'

    def deploy_build(self, cr, uid, vals, context=None):
        res = super(saas_base, self).deploy_build(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['app_code'] == 'gitlab':
            ssh, sftp = execute.connect(vals['container_fullname'], username='root', context=context)
            database_file = vals['service_full_localpath_files'] + '/config/database.yml'
            execute.execute(ssh, ['cp', vals['service_full_localpath_files'] + '/config/database.yml.postgresql', database_file], context)
            execute.execute(ssh, ['sed', '-i', 's/gitlabhq_production/' + vals['base_unique_name_'] + '/g', database_file], context)
            execute.execute(ssh, ['sed', '-i', 's/#\ username:\ git/username:\ ' + vals['service_db_user'] + '/g', database_file], context)
            execute.execute(ssh, ['sed', '-i', 's/#\ password:/password:\ ' + vals['service_db_password'] + '/g', database_file], context)
            execute.execute(ssh, ['sed', '-i', 's/#\ host:\ localhost/host:\ ' + vals['database_server'] + '/g', database_file], context)
            ssh.close()
            sftp.close()
        return res
