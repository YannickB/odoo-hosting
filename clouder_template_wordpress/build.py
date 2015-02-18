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
import re
import openerp.addons.clouder.execute as execute

import logging
_logger = logging.getLogger(__name__)

class clouder_application(osv.osv):
    _inherit = 'clouder.application'


class clouder_application_version(osv.osv):
    _inherit = 'clouder.application.version'

    def build_application(self, cr, uid, vals, context):
        super(clouder_application_version, self).build_application(cr, uid, vals, context)
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        if vals['apptype_name'] == 'wordpress':
            ssh, sftp = execute.connect('localhost', 22, 'clouder-conductor', context)
            execute.execute(ssh, ['wget', '-q', 'https://wordpress.org/latest.tar.gz', 'latest.tar.gz'], context, path=vals['app_version_full_archivepath'])
            execute.execute(ssh, ['tar', '-xzf', 'latest.tar.gz'], context, path=vals['app_version_full_archivepath'])
            execute.execute(ssh, ['mv', 'wordpress/*', './'], context, path=vals['app_version_full_archivepath'])
            execute.execute(ssh, ['rm', '-rf', './*.tar.gz'], context, path=vals['app_version_full_archivepath'])
            execute.execute(ssh, ['rm', '-rf', 'wordpress/'], context, path=vals['app_version_full_archivepath'])
            ssh.close()
            sftp.close()
        return