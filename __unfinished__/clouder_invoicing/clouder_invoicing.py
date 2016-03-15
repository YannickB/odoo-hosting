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

from openerp import models, fields, api, _
from openerp.exceptions import except_orm


class ClouderInvoicingPricegridLine(models.Model):
    """
    Defines a pricegrid line
    """
    _name = 'clouder.invoicing.pricegrid.line'

    invoicing_unit = fields.Many2one('clouder.application.metadata', 'Invoicing Unit')
    threshold = fields.Integer('Threshold', required=True)
    price = fields.Float('Price', required=True)
    type = fields.Selection(
        'Type',
        [
            ('fixed', 'Fixed Price'),
            ('mult', 'Value Multiplier')
        ],
        required=True
    )
    link_application = fields.Many2one('clouder.application', 'Application')
    link_container = fields.Many2one('clouder.container', 'Container')
    link_base = fields.Many2one('clouder.base', 'Base')

    @api.one
    @api.constrains('link_application', 'link_container', 'link_base')
    def _check_links(self):
        """
        Checks that at least one - and only one - of the three links is defined
        """
        # At least one should be defined
        if not self.link:
            raise except_orm(
                    _('Link error!'),
                    _("You cannot define a pricegrid line without linking it to a base or container or application.")
                )
        # No more than one should be defined
        if (self.link_base and self.link_application or
                self.link_base and self.link_container or
                self.link_application and self.link_container):
            raise except_orm(
                    _('Link error!'),
                    _("Pricegrid links to application/container/base are exclusive to one another.")
                )

    @property
    def link(self):
        """
        Returns the link defined
        """
        return self.link_application or self.link_container or self.link_base or False

    @property
    def link_type(self):
        """
        Returns a string that gives the type of the link
            Example: "clouder.base"
        """
        return self.link._name

    @property
    def invoicing_unit_value(self):
        """
        Returns the value from the invoicing unit metadata
        """
        return self.invoicing_unit.value


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
    invoicing_period = fields.Integer('Invoicing Period (days)', required=True)

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
    invoicing_period = fields.Integer('Invoicing Period (days)', required=True)
