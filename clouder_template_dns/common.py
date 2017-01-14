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


try:
    from odoo import models, api
except ImportError:
    from openerp import models, api


class ClouderBaseLink(models.Model):
    """
    Add method to manage links between bases and the bind service.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_dns_config(self, name, type, value):
        self.purge_dns_config(name, type)
        return

    @api.multi
    def purge_dns_config(self, name, type):
        return

    @api.multi
    def deploy_link(self):
        """
        Add a new A record when we create a new base, and MX if the
        base has a postfix link.
        """
        super(ClouderBaseLink, self).deploy_link()

        if self.name.check_tags(['dns']):
            proxy_link = self.search([
                ('base_id', '=', self.base_id.id),
                ('name.type_id.name', '=', 'proxy')])
            ip = proxy_link and proxy_link[0].target.node_id.public_ip or \
                self.base_id.service_id.node_id.public_ip

            if self.base_id.is_root:
                self.deploy_dns_config('@', 'A', ip)
            self.deploy_dns_config(self.base_id.name, 'A', ip)

            if proxy_link and proxy_link.target and not self.base_id.cert_key \
                    and not self.base_id.cert_cert:
                self.base_id.generate_cert_exec()

    @api.multi
    def purge_link(self):
        """
        Remove base records on the bind service.
        """
        super(ClouderBaseLink, self).purge_link()
        if self.name.check_tags(['dns']):
            if self.base_id.is_root:
                self.purge_dns_config('@', 'A')
            self.purge_dns_config(self.base_id.name, 'A')
