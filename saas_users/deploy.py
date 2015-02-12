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



class saas_container(osv.osv):
    _inherit = 'saas.container'

    def deploy_post(self, cr, uid, vals, context):
        super(saas_container, self).deploy_post(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'openldap':

            domain_dc = ''
            for dc in vals['container_options']['domain']['value'].split('.'):
                if domain_dc:
                    domain_dc += ','
                domain_dc += 'dc=' + dc

            server_obj = self.pool.get('ldap.server')
            server_obj.create(cr, uid, {
                'name': vals['container_fullname'],
                'host': vals['server_domain'],
                'port': vals['container_ports']['openldap']['hostport'],
                'binddn': 'cn=admin,' + domain_dc,
                'basedn': 'ou=people,' + domain_dc,
                'password': vals['container_options']['password']['value']
            })

    def purge(self, cr, uid, vals, context={}):
        if vals['apptype_name'] == 'openldap':
            server_obj = self.pool.get('ldap.server')
            server_ids = server_obj.search(cr, uid, [('host','=',vals['server_domain']),('port','=',vals['container_ports']['openldap']['hostport'])])
            server_obj.unlink(cr, uid, server_ids, context=context)
        return super(saas_container, self).purge(cr, uid, vals, context)