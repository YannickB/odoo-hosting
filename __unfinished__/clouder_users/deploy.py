# -*- coding: utf-8 -*-
##############################################################################
#
# Author: Yannick Buron
# Copyright 2015, TODAY Clouder SASU
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License with Attribution
# clause as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License with
# Attribution clause along with this program. If not, see
# <http://www.gnu.org/licenses/>.
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
import erppeek

import logging

_logger = logging.getLogger(__name__)


class clouder_container(osv.osv):
    _inherit = 'clouder.container'

    def deploy_post(self):
        super(clouder_container, self).deploy_post()
        if self.application_id.type_id.name == 'openldap':

            domain_dc = ''
            for dc in self.options['domain']['value'].split('.'):
                if domain_dc:
                    domain_dc += ','
                domain_dc += 'dc=' + dc

            hostport = False
            for port in self.port_ids:
                if port.name == 'openldap':
                    hostport = port.hostport

            server_obj = self.env['ldap.server']
            server_obj.create({
                'name': self.fullname,
                'host': self.server_id.name,
                'port': hostport,
                'binddn': 'cn=admin,' + domain_dc,
                'basedn': 'ou=people,' + domain_dc,
                'password': self.options['password']['value']
            })

    def purge(self):
        if self.application_id.type_id.name == 'openldap':

            hostport = False
            for port in self.port_ids:
                if port.name == 'openldap':
                    hostport = port.hostport

            server_obj = self.pool.get('ldap.server')
            server_ids = server_obj.search([
                ('host', '=', self.server_id.name), ('port', '=', hostport)])
            server_ids.unlink()
        return super(clouder_container, self).purge()