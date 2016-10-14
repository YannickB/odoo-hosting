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
from openerp import modules
from datetime import datetime

import socket


class ClouderDomain(models.Model):
    """
    """

    _inherit = 'clouder.domain'

    @api.multi
    def deploy(self):
        """

        """
        #if self.dns_id and self.dns_id.application_id.type_id.name == 'route53':
            # TODO configure root domain

    @api.multi
    def purge(self):
        """

        """
        #if self.dns_id and self.dns_id.application_id.type_id.name == 'bind':
            # TODO purge root domain

class ClouderBaseLink(models.Model):
    """
    Add method to manage links between bases and the bind container.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_link(self):
        """
        """
        super(ClouderBaseLink, self).deploy_link()
        # if self.name.type_id.name == 'route53':
            # TODO deploy domain

    @api.multi
    def purge_link(self):
        """
        """
        super(ClouderBaseLink, self).purge_link()
        # if self.name.type_id.name == 'route53':
            # TODO purge root domain
