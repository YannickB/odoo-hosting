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

from openerp import models, fields


class ClouderInvoicingConnection(models.Model):
    """
    Defines a connection to another clouder for invoicing purposes
    """
    _name = 'clouder.invoicing.connection'

    host = fields.Char('Clouder Invoicing Master Host', size=64, required=False)
    login = fields.Char('Clouder Invoicing Master Login', size=32, required=False)
    password = fields.Char('Clouder Invoicing Master Password', size=32, password=True, required=False)


class ClouderContainer(models.Model):
    """
    Defines invoicing settings for clouder child containers
    """
    _inherit = 'clouder.container'

    connection_id = fields.Many2One('clouder.invoicing.connection', 'Connection details')

    @api.multi
    def invoice_childs(self):
        """
        Create invoices for child clouder containers
        """
        # TODO:
        pass
