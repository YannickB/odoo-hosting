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

import time
from datetime import datetime, timedelta
import subprocess
import openerp.addons.saas.execute as execute

import logging
_logger = logging.getLogger(__name__)


class saas_application_version(osv.osv):
    _inherit = 'saas.application.version'

    def build_application(self, cr, uid, vals, context):
        super(saas_application_version, self).build_application(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'odoo':
            execute.execute_local(['mkdir', '-p', vals['app_version_full_archivepath'] + '/extra'], context)
            execute.execute_write_file(vals['app_version_full_archivepath'] + '/buildout.cfg', vals['app_buildfile'], context)
            execute.execute_local(['wget', 'https://raw.github.com/buildout/buildout/master/bootstrap/bootstrap.py'], context, path=vals['app_version_full_archivepath'])
            execute.execute_local(['virtualenv', 'sandbox'], context, vals['app_version_full_archivepath'])
            execute.execute_local(['yes | sandbox/bin/pip uninstall setuptools pip'], context, path=vals['app_version_full_archivepath'], shell=True)
            execute.execute_local(['sandbox/bin/python', 'bootstrap.py'], context, vals['app_version_full_archivepath'])
            execute.execute_local(['bin/buildout'], context, vals['app_version_full_archivepath'])

            #Can't make sed work on local
            ssh, sftp = execute.connect('localhost', 22, 'saas-conductor', context)
            execute.execute(ssh, ['patch', vals['app_version_full_archivepath'] + '/parts/odoo/openerp/http.py', '<', modules.get_module_path('saas_odoo') + '/res/http.patch'], context)
            execute.execute(ssh, ['sed', '-i', '"s/' + vals['config_archive_path'].replace('/','\/') + '/' + vals['apptype_localpath'].replace('/','\/') + '/g"', vals['app_version_full_archivepath'] + '/bin/start_odoo'], context)
            execute.execute(ssh, ['sed', '-i', '"s/' + vals['config_archive_path'].replace('/','\/') + '/' + vals['apptype_localpath'].replace('/','\/') + '/g"', vals['app_version_full_archivepath'] + '/bin/buildout'], context)
            ssh.close()
            sftp.close()
        return
