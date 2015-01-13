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
import openerp.addons.saas.execute as execute

import logging
_logger = logging.getLogger(__name__)


class saas_application_version(osv.osv):
    _inherit = 'saas.application.version'

    def build_application(self, cr, uid, vals, context):
        super(saas_application_version, self).build_application(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['app_code'] == 'gitlab':
            ssh, sftp = execute.connect('localhost', 22, 'saas-conductor', context)
            execute.execute(ssh,['git', 'clone', 'https://gitlab.com/gitlab-org/gitlab-ce.git', '-b', '7-5-stable', 'gitlab'], context, path=vals['app_version_full_archivepath'])
            execute.execute(ssh,['mv', 'gitlab/*', './'], context, path=vals['app_version_full_archivepath'])
            execute.execute(ssh,['rm', '-r', 'gitlab'], context, path=vals['app_version_full_archivepath'])
            ssh.close()
            sftp.close()

        return

