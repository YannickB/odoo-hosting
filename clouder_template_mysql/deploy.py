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


class clouder_container(osv.osv):
    _inherit = 'clouder.container'
    def deploy_post(self, cr, uid, vals, context):
        super(clouder_container, self).deploy_post(cr, uid, vals, context)
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        if vals['apptype_name'] == 'mysql':
            ssh, sftp = execute.connect(vals['container_fullname'], context=context)
            execute.execute(ssh, ['sed', '-i', '"/bind-address/d"', '/etc/mysql/my.cnf'], context)
            if vals['container_options']['root_password']['value']:
                password =vals ['container_options']['root_password']['value']
            else:
                password = execute.generate_random_password(20)
                option_obj = self.pool.get('clouder.container.option')
                option_ids = option_obj.search(cr, uid, [('container_id','=',vals['container_id']),('name','=','root_password')])
                if option_ids:
                    option_obj.write(cr, uid, option_ids, {'value': password}, context=context)
                else:
                    type_obj = self.pool.get('clouder.application.type.option')
                    type_ids = type_obj.search(cr, uid, [('apptype_id.name','=','mysql'),('name','=','root_password')])
                    if type_ids:
                        option_obj.create(cr, uid, {'container_id': vals['container_id'], 'name': type_ids[0], 'value': password}, context=context)
            execute.execute(ssh, ['mysqladmin', '-u', 'root', 'password', password], context)
