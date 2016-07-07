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
import logging

_logger = logging.getLogger(__name__)


class ClouderWebSession(models.Model):
    """
    A class to store session info from the external web form
    """
    _inherit = 'clouder.web.session'

    reference = fields.Char('Invoice Reference', required=False)


class ClouderWebHelper(models.Model):
    """
    A class made to be called by widgets and webpages alike
    """
    _inherit = 'clouder.web.helper'

    def make_invoice(self, session_id):
        """
        Makes all the necessary invoice actions and returns the invoice
        Also updates the session with the invoice reference
        """
        # TODO: implement the actual invoice part
        # TODO: update session with invoice ref
        return 0

    def get_payments_form(self, session_id, ref, amount):
        """
        Returns the payment form with working buttons, ready to be displayed
        """
        orm_pay_acq = self.env['payment.acquirer'].sudo()
        orm_clws = self.env['clouder.web.session'].sudo()

        session = orm_clws.browse([session_id])[0]

        html = orm_pay_acq.render_payment_block(ref, amount, False, partner_id=session.partner_id.id)

        # TODO: modify the form to return the session

        return html

    def call_payment(self, session_id, public_hostname):
        """
        Creates an invoice, generates the HTML form for payment and returns it
        """
        # TODO: make it a real invoice
        invoice_id = self.make_invoice(session_id)

        session = self.env['clouder.web.session'].sudo().browse([session_id])[0]
        ref = "TEST"+fields.Date.today()
        session.write({'reference': ref})

        # DEBUG TODO: remove test vals
        return self.get_payments_form(session_id, ref, 10)


class PaymentTransaction(models.Model):
    """
    A class to store session info from the external web form
    """
    _inherit = 'payment.transaction'

    def form_feedback(self, cr, uid, data, acquirer_name, context=None):
        # Process payment
        result = super(PaymentTransaction, self).form_feedback(cr, uid, data, acquirer_name, context=context)

        # Search for corresponding web session
        orm_clws = self.env['clouder.web.session'].sudo()
        session = orm_clws.search([('reference', '=', self.reference)])
        if session:
            session = session[0]

        # DEBUG TODO: if successfull make it validate the payment
        _logger.info(u"\n\nMEOW\n\n")
        _logger.info(u"\n\n{0}\n\n".format(session))
        if session:
            _logger.info(u"\n\n{0}\n\n".format(session.partner_id.name))

        return result
