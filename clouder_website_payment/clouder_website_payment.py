# -*- coding: utf-8 -*-
##############################################################################
#
# Author: Yannick Buron, Nicolas Petit
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

from openerp import models, fields, api, http, _
from openerp.exceptions import except_orm
import logging

_logger = logging.getLogger(__name__)


class ClouderApplication(models.Model):
    """
    Checks that the web create type has pricegrids
    """

    _inherit = 'clouder.application'

    @api.one
    @api.constrains('pricegrid_ids', 'web_create_type')
    def _check_create_type_pricegrids(self):
        if self.web_create_type != 'disabled' and not self.pricegrid_ids:
            raise except_orm(
                _('Application error!'),
                _("You cannot define a web creation type without defining price grids.")
            )

    @api.multi
    def create_instance_from_request(self, session_id):
        """
        Overwrite instance creation to set session status
        """
        created_id = super(ClouderApplication, self).create_instance_from_request(session_id)

        session = self.env['clouder.web.session'].browse([session_id])[0]

        # Change state to error by default
        state = 'error'

        # If the session was created successfully: change state to done
        if created_id:
            state = 'done'

        session.write({'state': state})

        return created_id


class AccountInvoice(models.Model):
    """
    Ovveride to create a function that will be run at startup to allow cancelled invoices on the sales journal
    """
    _inherit = 'account.invoice'

    def _make_sales_journal_cancellable(self):
        """
        Updates the default sales journal to allow invoice cancellation
        """
        journal = self._default_journal()
        journal.write({'update_posted': True})


class ClouderWebSession(models.Model):
    """
    Adds invoice reference to the new instance session
    """
    _inherit = 'clouder.web.session'

    amount = fields.Float('Amount to pay')
    reference = fields.Char('Invoice Reference', required=False)
    state = fields.Selection(
        [
            ('started', 'Started'),
            ('pending', 'Pending'),
            ('canceled', 'Cancelled'),
            ('payment_processed', 'Payment Processed'),
            ('error', 'Error'),
            ('done', 'Done')
        ],
        'State',
        default='started'
    )
    invoice_id = fields.Many2one('account.invoice', 'Invoice', required=False)

    @api.model
    def launch_update_with_invoice(self):
        """
        Search for sessions that have been paid and launch invoice creation
        """
        sessions = self.search([
            ('state', '=', 'payment_processed'),
            ('invoice_id', '=', False),
            ('amount', '!=', False)
        ])
        # No session meets the criteria: do nothing
        if not sessions:
            return

        orm_trans = self.env['payment.transaction']

        # Make an empty recordset
        sessions_to_update = sessions[0]
        sessions_to_update = sessions_to_update - sessions[0]

        for session in sessions:
            transac = orm_trans.search([('reference', '=', session.reference)])[0]

            # Add to the sessions to update is the transaction has been completed
            if transac.state == 'done':
                sessions_to_update = sessions_to_update + session

        # Launch invoice creation
        sessions_to_update.make_invoice()

    @api.multi
    def make_invoice(self):
        """
        Creates invoice and links it to the session
        """
        orm_inv = self.env['account.invoice']

        for session in self:
            # Check that the function isn't called with unsuitable sessions
            if session.state != 'payment_processed' or session.invoice_id:
                raise except_orm(
                    _('Clouder Web Session error!'),
                    _("You cannot launch invoice creation when a session is not process or already has an invoice")
                )

            # Creating invoice
            inv_desc = "{0} {1}".format(
                session.application_id.invoicing_product_id.description_sale,
                session.name
            )
            invoice_data = {
                'amount': session.amount,
                'partner_id': session.partner_id.id,
                'account_id': session.partner_id.property_account_receivable.id,
                'product_id': session.application_id.invoicing_product_id.id,
                'name': inv_desc,
                'origin': session.reference
            }
            invoice_id = orm_inv.clouder_make_invoice(invoice_data)
            invoice = orm_inv.browse([invoice_id])[0]
            session.write({'invoice_id': invoice.id})

            # Validating invoice to create reference number
            invoice.signal_workflow('invoice_open')

    @api.model
    def create_instances(self):
        """
        Creates an instance for suitable sessions
        """
        # Search for sessions that generated an invoice (payment is "done")
        sessions = self.search([
            ('invoice_id', '!=', False)
        ])
        # No session meets the criteria: do nothing
        if not sessions:
            return

        # Launch instance creation
        orm_app = self.env['clouder.application']
        for session in sessions:
            orm_app.create_instance_from_request(session.id)

    @property
    def should_unlink(self):
        """
        Returns true if the session should be pruned from the database
        """
        d_from_str = fields.Datetime.from_string
        last_access_days = (d_from_str(fields.Datetime.now()) - d_from_str(self.write_date)).days
        if self.state == 'started' and last_access_days > 9:
            return True
        elif self.state == 'cancelled' and last_access_days > 2:
            return True
        elif self.state == 'done':
            return True
        return False

    @api.model
    def prune_records(self):
        """
        Prune records that are marked as such
        Should not be called from a recordset!
        """
        for record in self.search([]):
            if record.should_unlink():
                record.unlink()


class PaymentTransaction(models.Model):
    """
    Override payment form to allow
    """
    _inherit = 'payment.transaction'

    def form_feedback(self, cr, uid, data, acquirer_name, context=None):
        # Process payment
        result = super(PaymentTransaction, self).form_feedback(cr, uid, data, acquirer_name, context=context)

        # Since this is an old-api definition we need to make the new environment ourselves
        env = api.Environment(cr, uid, context)

        # Search for corresponding web session
        orm_clws = env['clouder.web.session'].sudo()
        session = orm_clws.search([('reference', '=', data['item_number'])])

        # If no session is found, skip and proceed as usual
        if not session:
            return result
        session = session[0]

        # Finding transaction
        tx = None
        tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
        if hasattr(self, tx_find_method_name):
            tx = getattr(self, tx_find_method_name)(cr, uid, data, context=context)

        if tx and tx.state in ['cancel', 'error']:
            # Cancel session
            session.write({'state', 'canceled'})
        elif tx and tx.state in ['pending', 'done']:
            # Change session state
            session.write({'state': 'payment_processed'})

        # Return the result from super at the end
        return result
