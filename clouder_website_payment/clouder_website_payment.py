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
    Adds invoice reference to the new instance session
    """
    _inherit = 'clouder.web.session'

    reference = fields.Char('Invoice Reference', required=False)


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
        orm_clws = env['clouder.web.session']
        session = orm_clws.search([('reference', '=', data['item_number'])])
        if session:
            session = session[0]

        # DEBUG TODO: if successfull make it launch instance creation
        _logger.info(u"\n\nMEOW\n\n")
        _logger.info(u"\n\n{0}\n\n".format(session))
        if session:
            _logger.info(u"\n\n{0}\n\n".format(session.partner_id.name))

        return result
