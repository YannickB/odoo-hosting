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


class ClouderInvoicingPriceGridLine(models.Model):
    """
    Defines a price grid line
    """
    _name = 'clouder.invoicing.pricegrid.line'

    threshold = fields.Integer('Threshold', required=True)
    price = fields.Float('Price', required=True)
    type = fields.Selection('Type',
        [
            ('fixed', 'Fixed Price'),
            ('mult', 'Value Multiplier')
        ],
        required=True)
    link_application = fields.Many2one('clouder.application', 'Application')
    link_container = fields.Many2one('clouder.container', 'Container')
    link_base = fields.Many2one('clouder.base', 'Base')

    @api.one
    @api.constrains('link_application', 'link_container', 'link_base')
    def _check_links(self):
        """
        Checks that one and only one of the three links is defined
        """
        # TODO:
        pass

    @property
    def link(self):
        """
        Returns the link defined
        """
        # TODO:
        pass

    @property
    def link_type(self):
        """
        Returns a string that gives the type of the link
            Example: "clouder.base"
        """
        # TODO:
        pass


class ClouderInvoicingConnection(models.Model):
    """
    Defines a connection to another clouder for invoicing purposes
    """

    _name = 'clouder.invoicing.connection'

    host = fields.Char('Clouder Invoicing Master Host', size=64, required=False)
    login = fields.Char('Clouder Invoicing Master Login', size=32, required=False)
    password = fields.Char('Clouder Invoicing Master Password', size=32, password=True, required=False)


class ClouderInvoicingSettings(models.TransientModel):
    """
    Defines invoicing settings for clouder
    """
    _inherit = 'res.config.settings'
    _name = 'clouder.invoicing.settings'

    connection_id = fields.Many2one('clouder.invoicing.connection', 'Master Clouder Connection Info')
    master_enabled = fields.Boolean('Invoicing Master connection enabled?')

    @api.depends('master_enabled', 'connection_id')
    def _check_enabled(self):
        """
        Checks if a connection_id is defined is master_enabled is set to true
        """
        # TODO:
        pass


class ClouderApplication(models.Model):
    """
    Defines invoicing settings for an application
    """
    _inherit = 'clouder.application'

    pricegrid_ids = fields.One2many(
        'clouder.invoicing.pricegrid.line',
        'link_application',
        'Pricegrids'
    )

    @api.multi
    def generate_grids(self):
        """
        Use application-defined metadata to compute the price grid
        """
        # TODO:
        pass


class ClouderContainer(models.Model):
    """
    Defines invoicing settings for an application
    """
    _inherit = 'clouder.container'

    pricegrid_ids = fields.One2many(
        'clouder.invoicing.pricegrid.line',
        'link_container',
        'Pricegrids'
    )

    @api.multi
    def create_invoice(self, price_from_master=None):
        """
        Creates an invoice using the pricegrid lines and metadata from the application/container/base
        :param: price_from_master - it set to a numerical value, will only generate a supplier invoice with that amount
        """
        # TODO:
        pass


class ClouderBase(models.Model):
    """
    Defines invoicing settings for an application
    """
    _inherit = 'clouder.base'

    pricegrid_ids = fields.One2many(
        'clouder.invoicing.pricegrid.line',
        'link_base',
        'Pricegrids'
    )
