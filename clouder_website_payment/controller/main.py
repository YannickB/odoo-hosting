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

from openerp import http, _
from openerp.http import request
from openerp.addons.clouder_website.controller.main import FormController
import json
import logging

_logger = logging.getLogger(__name__)

HEADERS = [('Access-Control-Allow-Origin', '*')]


class FormControllerExtend(FormController):
    """
    Extends clouder_website's HTTP controller to add payment capabilities
    """

    def hook_next(self, data):
        """
        Returns the payment form after the basic form was submitted
        """
        #orm_clwh = request.env['clouder.web.helper'].sudo()
        #html = orm_clwh.call_payment(data['result']['session_id'], request.httprequest.url_root)

        orm_cpny = request.env['res.company'].sudo()
        company_id = orm_cpny._company_default_get('res.partner')

        orm_clws = request.env['clouder.web.session'].sudo()
        session = orm_clws.browse([data['result']['session_id']])[0]

        # TODO: use real values instead
        from openerp import fields
        ref = "TEST"+fields.Date.today()
        amount = 10
        currency_id = False
        # END TODO

        orm_acq = request.env['payment.acquirer'].sudo()
        acquirers = []
        render_ctx = dict(request.context, submit_class='btn btn-primary', submit_txt=_('Pay Now'))
        for acquirer in orm_acq.search([('website_published', '=', True), ('company_id', '=', company_id)]):
            acquirer.button = acquirer.with_context(**render_ctx).render(
                ref,
                amount,
                currency_id,
                partner_id=session.partner_id.id,
                tx_values={}
            )[0]
            acquirers.append(acquirer)

        qweb_context = {
            'acquirers': acquirers,
            'hostname': request.httprequest.url_root
        }

        html = request.env.ref('clouder_website_payment.clouder_web_payment_buttons').render(
            qweb_context,
            engine='ir.qweb',
            context=request.context
        )

        html += self.include_run_js('clouder_website_payment/static/src/js/clouder_website_payment.js')

        resp = {
            'html': html,
            'div_id': 'CL_payment',
        }

        return request.make_response(json.dumps(resp), headers=HEADERS)
