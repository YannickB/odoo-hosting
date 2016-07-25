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
    
    def _get_application_id(self):
        object = self.link
        if self.link._name != 'clouder.application':
            object = self.link.application_id
        return object

    application_id = fields.Many2one('clouder.application', 'Application', compute='_get_application_id', store=True)
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
    @api.constrains('link_application', 'link_container', 'link_base', 'application_metadata')
    def _check_links_and_metadata(self):
        """
        Checks that at least one - and only one - of the three links is defined
        Checks that the application_metadata has the right application id
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

        # Update application_id since the links may have changed
        self.application_id = self._get_application_id()[0]

        if self.application_id.id != self.application_metadata.application_id.id:
            raise except_orm(
                _('Pricegrid error!'),
                _("The metadata should be associated with the same application as the pricegrid.")
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
                        _("This function should only be called from a set of records " +
                          "linked to the same container OR base OR application.")
                    )
        # Grouping lines by invoicing unit
        invoicing_data = {}
        for pgl in self:
            if pgl.application_metadata.id not in invoicing_data:
                invoicing_data[pgl.application_metadata.id] = {}
            if pgl.type not in invoicing_data[pgl.application_metadata.id]:
                invoicing_data[pgl.application_metadata.id][pgl.type] = []
            invoicing_data[pgl.application_metadata.id][pgl.type].append(pgl)

        # Sorting resulting lists by threshold
        for k, v in invoicing_data.iteritems():
            for table in v:
                v[table].sort(key=lambda x: x.threshold)

        # Computing final value*
        amount = 0.0
        for tables in invoicing_data.values():
            for k, lines in tables.iteritems():
                compare_unit = lines[0].invoicing_unit
                index = 0

                # No amount to add if the first threshold is above current compare value
                if lines[index].threshold > compare_unit:
                    continue

                # Searching for the right line
                while (index+1) < len(lines) and lines[index+1].threshold <= compare_unit:
                    index += 1

                # Computing and adding price
                if lines[index].type == 'fixed':
                    amount += lines[index].price
                elif lines[index].type == 'mult':
                    amount += lines[index].price * compare_unit
                else:
                    # Preventing possible future type errors
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

    @api.model
    def _get_default_product(self):
        product = self.env.ref('clouder_invoicing.container_instance_product', False) and \
            self.env.ref('clouder_invoicing.container_instance_product') or \
            self.env['product.product']
        return product

    pricegrid_ids = fields.One2many(
        'clouder.invoicing.pricegrid.line',
        'link_application',
        'Pricegrids'
    )
    invoicing_product_id = fields.Many2one(
        'product.product',
        string="Invoicing product",
        default=_get_default_product
    )
    initial_invoice_amount = fields.Float(
        'Instance Creation Fees',
        help="""This is the price to pay once at instance creation.
        This price is manually set and unrelated to price grids computation."""
    )

    @api.one
    @api.constrains('initial_invoice_amount')
    def _check_initial_invoice_amount_positive(self):
        if self.initial_invoice_amount < 0.0:
            raise except_orm(
                _('Application invoice error!'),
                _("You cannot set a negative amount as instance creation fees.")
            )

    @api.one
    @api.constrains('pricegrid_ids', 'invoicing_product_id')
    def _check_pricegrid_product(self):
        """
        Checks that the invoicing product is set if there are pricegrids
        """
        if self.pricegrid_ids and not self.invoicing_product_id:
            raise except_orm(
                _('Application pricegrid error!'),
                _("An application with pricegrids must have an invoicing product set.")
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

    @api.multi
    def should_invoice(self):
        """
        Returns a boolean telling if the container should be invoiced or not
        """
        self.ensure_one()
        if not self.invoicing_period:
            return False

        today = fields.Date.from_string(fields.Date.today())

        days_diff = (today - fields.Date.from_string(self.last_invoiced)).days
        days_needed = (
            (
                fields.Date.from_string(self.last_invoiced) + relativedelta(months=self.invoicing_period)
            ) - fields.Date.from_string(self.last_invoiced)
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
                    if base.should_invoice() and base.pricegrid_ids:
                        results['invoice_base_data'].append({
                            'id': base.id,
                            'product_id': base.application_id.invoicing_product_id,
                            'partner_id': base.environment_id.partner_id.id,
                            'account_id': base.environment_id.partner_id.property_account_receivable.id,
                            'amount': base.pricegrid_ids.invoice_amount()
                        })
            elif container.should_invoice() and container.pricegrid_ids:
                # Invoicing per container
                results['invoice_container_data'].append({
                    'id': container.id,
                    'product_id': container.application_id.invoicing_product_id,
                    'partner_id': container.environment_id.partner_id.id,
                    'account_id': container.environment_id.partner_id.property_account_receivable.id,
                    'amount': container.pricegrid_ids.invoice_amount()
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
        if 'container_id' in vals and vals['container_id']:
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

    @api.multi
    def should_invoice(self):
        """
        Returns a boolean telling if the container should be invoiced or not
        """
        self.ensure_one()
        if not self.invoicing_period:
            return False

        today = fields.Date.from_string(fields.Date.today())

        days_diff = (today - fields.Date.from_string(self.last_invoiced)).days
        days_needed = (
            (
                fields.Date.from_string(self.last_invoiced) + relativedelta(months=self.invoicing_period)
            ) - fields.Date.from_string(self.last_invoiced)
        ).days

        return days_diff >= days_needed


class AccountInvoice(models.Model):
    """
    Overrides invoices to allow invoicing operations on clouder instances
    """
    _inherit = "account.invoice"

    @api.model
    def clouder_make_invoice(self, data):
        """
        Creates an invoice from clouder data
        """
        orm_accline = self.env['account.invoice.line']

        invoice = self.create({
            'origin': data['origin'],
            'partner_id': data['partner_id'],
            'account_id': data['account_id']
        })

        line_data = {
            'invoice_id': invoice.id,
            'origin': data['origin'],
            'product_id': data['product_id'],
            'price_unit': data['amount']
        }

        if 'name' in data:
            line_data['name'] = data['name']

        orm_accline.create(line_data)

        return invoice.id

    @api.model
    def clouder_invoice_containers(self, containers):
        """
        Launch invoice-related data gathering for container and their linked bases,
        the use that data to create relevant invoices.
        """
        def make_invoice_and_update(orm_class, data):
            instance = orm_class.browse([data['id']])[0]
            origin = instance.name + "_" + fields.Date.today()

            inv_data = {
                'origin': origin,
                'partner_id': data['partner_id'],
                'product_id': data['product_id'],
                'account_id': data['account_id'],
                'amount': data['amount']
            }
            if 'name' in data:
                inv_data['name'] = data['name'],

            invoice = self.clouder_make_invoice(inv_data)
            
            # Updating date for instance
            instance.write({'last_invoiced': fields.Date.today()})

            return invoice.id

        orm_cont = self.env['clouder.container']
        orm_base = self.env['clouder.base']

        result = {
            'containers': {},
            'bases': {}
        }

        # Gathering invoice data from containers
        invoice_data = containers.get_invoicing_data()

        # Processing containers
        for container_data in invoice_data['invoice_container_data']:
            invoice_id = make_invoice_and_update(orm_cont, container_data)
            result['containers'][container_data['id']] = invoice_id

        # Processing bases
        for base_data in invoice_data['invoice_base_data']:
            invoice_id = make_invoice_and_update(orm_base, base_data)
            result['containers'][base_data['id']] = invoice_id
        return result

    @api.model
    def clouder_invoicing(self):
        """
        Launch invoicing on all existing instances
        """
        # Getting all containers
        containers = self.env['clouder.container'].search([])
        self.clouder_invoice_containers(containers)

    @api.model
    def create_clouder_supplier_invoice(self, amount):
        """
        Creates a supplier invoice from the master clouder with the given amount
        """
        # TODO: create a real invoice
        _logger.info('\nINVOICING FROM MASTER FOR {0}\n'.format(amount))

        # TODO: return invoice ID or -1 if it fails
        return 0
