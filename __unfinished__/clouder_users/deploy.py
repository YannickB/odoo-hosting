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

from openerp import models, api


class ClouderContainer(models.Model):
    """
    Manage link between ldap.server object and ldap service.
    """

    _inherit = 'clouder.service'

    @api.multi
    def deploy_post(self):
        """
        Add a ldap.server in clouder when we create a new ldap service.
        """
        super(ClouderContainer, self).deploy_post()
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
        """
        Remove the ldap.server in clouder when we unlink an ldap service.
        """
        if self.application_id.type_id.name == 'openldap':

            hostport = False
            for port in self.port_ids:
                if port.name == 'openldap':
                    hostport = port.hostport

            server_obj = self.pool.get('ldap.server')
            server_ids = server_obj.search([
                ('host', '=', self.server_id.name), ('port', '=', hostport)])
            server_ids.unlink()
        return super(ClouderContainer, self).purge()