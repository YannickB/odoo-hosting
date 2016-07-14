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

    @api.one
    @api.constraints('pricegrid_ids', 'web_create_type')
    def _check_create_type_pricegrids(self):
        if self.web_create_type != 'disabled' and not self.pricegrid_ids:
            raise except_orm(
                _('Application error!'),
                _("You cannot define a web creation type without defining price grids.")
            )


class ClouderWebSession(models.Model):
    """
    Adds invoice reference to the new instance session
    """
    _inherit = 'clouder.web.session'

    reference = fields.Char('Invoice Reference', required=False)
    state = fields.Selection(
        [
            ('started', 'Started'),
            ('canceled', 'Cancelled'),
            ('payment_processed', 'Payment Processed'),
            ('done', 'Done')
        ],
        'State',
        default='started'
    )

    @api.property
    def should_unlink(self):
        """
        Returns true if the session should be pruned from the database
        """
        d_from_str = fields.Datetime.from_string
        last_access_days = (d_from_str(fields.Datetime.now()) - d_from_str(self.write_date)).days
        if self.state == 'started' and last_access_days > 5:
            return True
        elif self.state == 'cancelled' and last_access_days > 1:
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

        # Finding transaction
        tx = None
        tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
        if hasattr(self, tx_find_method_name):
            tx = getattr(self, tx_find_method_name)(cr, uid, data, context=context)

        # At this point there should never be a case where there is no found invoice
        session = session[0]
        orm_inv = env['account.invoice'].sudo()
        invoice = orm_inv.search([('internal_number', '=', session.reference)])[0]

        if tx and tx.state == 'cancel':
            # Cancel session and invoice
            session.write({'state', 'canceled'})
            invoice.action_cancel()
        else:
            # Launch instance creation
            env['clouder.application'].sudo().create_instance_from_request(session.id)

            # Confirm invoice and change session state
            invoice.invoice_validate()
            session.write({'state': 'payment_processed'})

            # TODO: Reconcile payment if the payment is already done ?
            if tx.state == 'done':
                pass

        # Return the result from super at the end
        return result
