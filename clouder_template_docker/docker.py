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
import paramiko
import execute

import logging
_logger = logging.getLogger(__name__)


class clouder_container(osv.osv):
    _inherit = 'clouder.container'

    def write(self, cr, uid, ids, vals, context=None):
        res = super(clouder_container, self).write(cr, uid, ids, vals, context)
        for container in self.browse(cr, uid, ids, context=context):
            if 'option_ids' in vals:
                container_vals = self.get_vals(cr, uid, container.id, context=context)
                if container_vals['apptype_name'] == 'docker' and 'public_key' in container_vals['container_options']:
                    self.deploy_post(cr, uid, container_vals, context)
        return res

    def create_vals(self, cr, uid, vals, context={}):
        super(clouder_container, self).create_vals(cr, uid, vals, context)
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        if context['apptype_name'] == 'docker':
            start_port = ''
            end_port = ''
            type_option_obj = self.pool.get('clouder.application.type.option')
            if 'option_ids' in vals:
                _logger.info('test %s', vals['option_ids'])
                for option in vals['option_ids']:
                    _logger.info('test %s', option)
                    option = option[2]
                    type_option = type_option_obj.browse(cr, uid, option['name'], context=context)
                    if type_option.name == 'start_port':
                        start_port = option['value']
                    if type_option.name == 'end_port':
                        end_port = option['value']
            if start_port and end_port:
                start_port = int(start_port)
                end_port = int(end_port)
                if start_port < end_port:
                    i = start_port
                    while i <= end_port:
                        vals['port_ids'].append((0,0,{'name':str(i),'localport':str(i),'hostport':str(i),'expose':'internet'}))
                        i += 1
                else:
                    raise osv.except_osv(_('Data error!'),
                    _("Start port need to be inferior to end port"))
            else:
                raise osv.except_osv(_('Data error!'),
                _("You need to specify a start and end port"))

        return vals

    def deploy_post(self, cr, uid, vals, context):
        super(clouder_container, self).deploy_post(cr, uid, vals, context)
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        if vals['apptype_name'] == 'docker':
            if 'public_key' in vals['container_options']:
                ssh, sftp = execute.connect(vals['container_fullname'], context=context)
                execute.execute(ssh, ['echo "' + vals['container_options']['public_key']['value'] + '" > /root/.ssh/authorized_keys2'], context)

