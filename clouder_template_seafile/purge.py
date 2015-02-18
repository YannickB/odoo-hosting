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
import openerp.addons.clouder.execute as execute

import logging
_logger = logging.getLogger(__name__)




class clouder_base(osv.osv):
    _inherit = 'clouder.base'

    def purge_post(self, cr, uid, vals, context):
        super(clouder_base, self).purge_post(cr, uid, vals, context)
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        if vals['apptype_name'] == 'seafile':
            ssh, sftp = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/program:' + vals['base_unique_name'] + '-seafile/d"', '/opt/seafile/supervisor.conf'], context)
            execute.execute(ssh, ['sed', '-i', '"/' + vals['service_full_localpath_files'].replace('/','\/') + '\/seafile.sh/d"', '/opt/seafile/supervisor.conf'], context)
            execute.execute(ssh, ['sed', '-i', '"/program:' + vals['base_unique_name'] + '-seahub/d"', '/opt/seafile/supervisor.conf'], context)
            execute.execute(ssh, ['sed', '-i', '"/' + vals['service_full_localpath_files'].replace('/','\/') + '\/seahub.sh/d"', '/opt/seafile/supervisor.conf'], context)
            ssh.close()
            sftp.close()