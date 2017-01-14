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

import logging

try:
    from odoo import models, api
except ImportError:
    from openerp import models, api

_logger = logging.getLogger(__name__)

try:
    from libcloud.dns.providers import get_driver
    from libcloud.dns.types import Provider
    from libcloud.dns.types import RecordType
except ImportError:
    _logger.warning('Cannot `import libcloud`.')


class ClouderDomain(models.Model):
    """
    """

    _inherit = 'clouder.domain'

    @api.multi
    def deploy(self):
        """

        """

        super(ClouderDomain, self).deploy()

        if self.dns_id and \
                self.dns_id.application_id.type_id.name == 'clouddns':

            Driver = get_driver(getattr(Provider, self.provider_id.name))
            driver = Driver(
                self.provider_id.login, self.provider_id.secret_key)

            # Create a new zone
            driver.create_zone(domain=self.name)

    @api.multi
    def purge(self):
        """

        """
        if self.dns_id and \
                self.dns_id.application_id.type_id.name == 'clouddns':

            Driver = get_driver(getattr(Provider, self.provider_id.name))
            driver = Driver(
                self.provider_id.login, self.provider_id.secret_key)

            zones = driver.list_zones
            for zone in zones:
                if zone.domain == self.name:
                    driver.delete_zone(zone)


class ClouderBaseLink(models.Model):
    """
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_dns_config(self, name, type, value):
        super(ClouderBaseLink, self).deploy_dns_config(name, type, value)

        if self.name.type_id.name == 'clouddns':

            Driver = get_driver(
                getattr(Provider, self.target.provider_id.name))
            driver = Driver(
                self.provider_id.login, self.target.provider_id.secret_key)

            zones = driver.list_zones
            for zone in zones:
                if zone.domain == self.base_id.domain_id.name:
                    zone.create_record(
                        name=name, type=getattr(RecordType, type),
                        data=value)

    @api.multi
    def purge_dns_config(self, name, type):

        super(ClouderBaseLink, self).purge_dns_config(name, type)

        if self.name.type_id.name == 'clouddns':

            Driver = get_driver(
                getattr(Provider, self.target.provider_id.name))
            driver = Driver(
                self.provider_id.login, self.target.provider_id.secret_key)

            zones = driver.list_zones
            for zone in zones:
                if zone.domain == self.base_id.domain_id.name:
                    records = driver.list_records(zone)
                    for record in records:
                        if record.name == name and \
                                record.type == getattr(RecordType, type):
                            driver.delete_record(record)
