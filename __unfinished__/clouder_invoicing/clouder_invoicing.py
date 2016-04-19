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
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ClouderInvoicingPricegridLine(models.Model):
    """
    Defines a pricegrid line
    """
    _name = 'clouder.invoicing.pricegrid.line'

    application_metadata = fields.Many2one('clouder.application.metadata', 'Invoicing Unit', required=True)
    threshold = fields.Integer('Threshold', required=True)
    price = fields.Float('Price', required=True)
    type = fields.Selection(
        string="Type",
        selection=[
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
                _('Pricegrid error!'),
                _("You cannot define a pricegrid line without linking it to a base or container or application.")
            )
        # No more than one should be defined
        if (self.link_base and self.link_application or
                self.link_base and self.link_container or
                self.link_application and self.link_container):
            raise except_orm(
                _('Pricegrid error!'),
                _("Pricegrid links to application/container/base are exclusive to one another.")
            )

    @property
    def link(self):
        """
        Returns the link defined
        """
        return self.link_application or self.link_container or self.link_base

    @property
    def link_type(self):
        """
        Returns a string that gives the type of the link
            Example: "clouder.base"
        """
        return self.link._name

    @property
    def invoicing_unit(self):
        """
        Returns the invoicing unit of a pricegrid line
        """
        class_to_search = self.link_type + ".metadata"
        class_link = self.link_type.split('.')[-1] + "_id"

        # Search for the metadata
        metadata = self.env[class_to_search].search([
            (class_link, '=', self.link.id),
            ('name', '=', self.application_metadata.id)
        ])
        if not metadata:
            raise except_orm(
                _('Pricegrid invoicing_unit error!'),
                _("No linked metadata found for {0} '{1}'".format(self.link_type, self.link.name))
            )

        return metadata[0].value

    @api.multi
    def invoice_amount(self):
        """
        Given pricegrid lines for a single container/base: computes the amount to invoice
        """
        # Check that all lines are linked to the same object
        linked_recs = []
        for pgl in self:
            if pgl.link not in linked_recs:
                linked_recs.append(pgl.link)
                if len(linked_recs) > 1:
                    raise except_orm(
                        _('Pricegrid invoice_amount error!'),
                        _("This function should only be called from recordsets linked to the same container/base.")
                    )
        # Key for hash: pgl.invoicing_unit_metadata.id
        # Grouping lines by invoicing unit
        invoicing_data = {}
        for pgl in self:
            if pgl.invoicing_unit_metadata.id not in invoicing_data:
                invoicing_data[pgl.invoicing_unit_metadata.id] = []
            invoicing_data[pgl.invoicing_unit_metadata.id].append(pgl)

        # Sorting resulting lists by threshold
        for k, v in invoicing_data:
            invoicing_data[k] = v.sort(key=lambda x: x.threshold)

        # Computing final value*
        amount = 0.0
        for lines in invoicing_data.values():
            compare_unit = lines[0].invoicing_unit
            index = 0
            # Searching for the right line
            while index < len(lines) and compare_unit <= lines[index].threshold:
                index += 1

            # Computing and adding price
            if lines[index].type == 'fixed':
                amount += lines[index].price
            elif lines[index].type == 'mult':
                amount += lines[index].price * compare_unit
            else:
                # Preventing future possible errors
                raise except_orm(
                    _('Pricegrid invoice_amount error!'),
                    _(
                        "Unknown type '{0}' in pricegrid line for {1} '{2}'.".format(
                            lines[index].type,
                            lines[index].link_type,
                            lines[index].link.name
                        )
                    )
                )
        return amount


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

    def _compute_last_invoiced_default(self):
        """
        Computes the default value for the last_invoiced field
        """
        return fields.Date.today()

    pricegrid_ids = fields.One2many(
        'clouder.invoicing.pricegrid.line',
        'link_container',
        'Pricegrids'
    )
    invoicing_period = fields.Integer(
        'Invoicing Period (months)',
        default=1,
        help="The period separating two invoices.\n" +
             "Set to nothing to disable invoicing for this container."
    )
    last_invoiced = fields.Date('Last Invoiced', required=True, default=_compute_last_invoiced_default)

    @api.multi
    def get_default_pricegrids(self, vals):
        """
        Get default pricegrids from application
        """
        if vals['application_id']:
            application = self.env['clouder.application'].browse([vals['application_id']])[0]
            pricegrids = []

            # Adding default pricegrids from application
            for app_pricegrid in application.pricegrid_ids:
                pricegrids.append((0, 0, {
                    'application_metadata': app_pricegrid.application_metadata.id,
                    'threshold': app_pricegrid.threshold,
                    'price': app_pricegrid.price,
                    'type': app_pricegrid.type
                }))
            vals['pricegrid_ids'] = pricegrids

        return vals

    @api.onchange('application_id')
    def onchange_application_id_pricegrids(self):
        """
        Reset pricegrids to default when changing application
        """
        # Getting default pricegrids
        vals = {'application_id': self.application_id.id}
        vals = self.get_default_pricegrids(vals)

        # Replacing old pricegrids
        if 'pricegrid_ids' in vals:
            self.pricegrid_ids = vals['pricegrid_ids']

    @api.model
    def create(self, vals):
        """
        Override create to add default pricegrids from application
        """
        vals = self.get_default_pricegrids(vals)
        return super(ClouderContainer, self).create(vals)

    @api.one
    def should_invoice(self):
        """
        Returns a boolean telling if the container should be invoiced or not
        """
        if not self.invoicing_period:
            return False

        today = fields.Date.from_string(fields.Date.today())

        days_diff = (today - fields.Date.from_string(self.last_invoiced)).days
        days_needed = (
            (
                fields.Date.from_string(self.last_invoiced) + relativedelta(months=1)
            ) - today
        ).days

        return days_diff >= days_needed

    @api.multi
    def get_invoicing_data(self):
        # Preparing results
        results = {
            'invoice_base_data': [],
            'invoice_container_data': []
        }

        for container in self:
            if container.base_ids:
                # Invoicing per base
                for base in container.base_ids:
                    if base.should_invoice():
                        results['invoice_base_data'].append({
                            'id': base.id,
                            'amount': base.pricegrid_ids.invoice_amount
                        })
            elif container.should_invoice():
                # Invoicing per container
                results['invoice_container_data'].append({
                    'id': container.id,
                    'amount': container.pricegrid_ids.invoice_amount
                })
        return results


class ClouderBase(models.Model):
    """
    Defines invoicing settings for an application
    """
    _inherit = 'clouder.base'

    def _compute_last_invoiced_default(self):
        """
        Computes the default value for the last_invoiced field
        """
        return fields.Date.today()

    pricegrid_ids = fields.One2many(
        'clouder.invoicing.pricegrid.line',
        'link_base',
        'Pricegrids'
    )
    invoicing_period = fields.Integer(
        'Invoicing Period (months)',
        default=1,
        help="The period separating two invoices.\n" +
             "Set to nothing to disable invoicing for this container."
    )
    last_invoiced = fields.Date('Last Invoiced', required=True, default=_compute_last_invoiced_default)

    @api.multi
    def get_default_pricegrids(self, vals):
        """
        Get default pricegrids from container
        """
        if vals['container_id']:
            container = self.env['clouder.container'].browse([vals['container_id']])[0]
            pricegrids = []

            # Adding default pricegrids from application
            for cont_pricegrid in container.pricegrid_ids:
                pricegrids.append((0, 0, {
                    'application_metadata': cont_pricegrid.application_metadata.id,
                    'threshold': cont_pricegrid.threshold,
                    'price': cont_pricegrid.price,
                    'type': cont_pricegrid.type
                }))
            vals['pricegrid_ids'] = pricegrids

        return vals

    @api.onchange('container_id')
    def onchange_container_id_pricegrids(self):
        """
        Reset pricegrids to default when changing application
        """
        # Getting default pricegrids
        vals = {'container_id': self.container_id.id}
        vals = self.get_default_pricegrids(vals)

        # Replacing old pricegrids
        if 'pricegrid_ids' in vals:
            self.pricegrid_ids = vals['pricegrid_ids']

    @api.model
    def create(self, vals):
        """
        Override create to add default pricegrids from container
        """
        vals = self.get_default_pricegrids(vals)
        return super(ClouderBase, self).create(vals)

    @api.one
    def should_invoice(self):
        """
        Returns a boolean telling if the container should be invoiced or not
        """
        if not self.invoicing_period:
            return False

        today = fields.Date.from_string(fields.Date.today())

        days_diff = (today - fields.Date.from_string(self.last_invoiced)).days
        days_needed = (
            (
                fields.Date.from_string(self.last_invoiced) + relativedelta(months=1)
            ) - today
        ).days

        return days_diff >= days_needed


class AccountInvoice(models.Model):
    """
    Overrides invoices to allow supplier invoice from possible master clouder
    """
    _inherit = "account.invoice"

    @api.model
    def clouder_invoicing(self):
        """
        Invoice containers
        """
        container_env = self.env['clouder.container']
        base_env = self.env['clouder.base']

        # Getting all containers
        containers = container_env.search([])

        # Gathering invoice data from containers
        invoice_data = containers.get_invoicing_data()

        # Processing containers
        for container_data in invoice_data['invoice_container_data']:
            # TODO: create a real invoice
            _logger.info('\nINVOICING CONTAINER {0} FOR {1}\n'.format(container_data['id'], container_data['amount']))

            # Updating date for container
            c_ids = container_data.search([('id', '=', container_data['id'])])
            c_ids.write({'last_invoiced': fields.Date.today()})

        # Processing bases
        for base_data in invoice_data['invoice_base_data']:
            # TODO: create a real invoice
            _logger.info('\nINVOICING BASE {0} FOR {1}\n'.format(base_data['id'], base_data['amount']))

            # Updating date for base
            b_ids = base_env.search([('id', '=', base_data['id'])])
            b_ids.write({'last_invoiced': fields.Date.today()})
            b_ids.container.update_invoice_data()

    def create_clouder_supplier_invoice(self, amount):
        """
        Creates a supplier invoice from the master clouder with the given amount
        """
        # TODO: create a real invoice
        _logger.info('\nINVOICING FROM MASTER FOR {0}\n'.format(amount))
