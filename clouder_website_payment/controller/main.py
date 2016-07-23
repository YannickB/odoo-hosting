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

from openerp import http, _, fields
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
        orm_clws = request.env['clouder.web.session'].sudo()
        orm_acq = request.env['payment.acquirer'].sudo()

        session = orm_clws.browse([data['result']['clws_id']])[0]
        company = request.env.ref('base.main_company')

        # Saving reference and amount
        session.write({
            'reference': "{0}_{1}".format(session.name, fields.Date.today()),
            'amount': session.application_id.initial_invoice_amount
        })

        # If instance creation is free, we just get to the creation process
        if not session.amount:
            return super(FormControllerExtend, self).hook_next(data)

        # Setting acquirer buttons
        acquirers = []
        render_ctx = dict(request.context, submit_class='btn btn-primary', submit_txt=_('Pay Now'))
        for acquirer in orm_acq.search([('website_published', '=', True), ('company_id', '=', company.id)]):
            acquirer.button = acquirer.with_context(**render_ctx).render(
                session.reference,
                session.amount,
                company.currency_id.id,
                partner_id=session.partner_id.id,
                tx_values={
                    'return_url': '/clouder_form/payment_complete',
                    'cancel_url': '/clouder_form/payment_cancel'
                }
            )[0]
            acquirers.append(acquirer)

        # Render the form
        qweb_context = {
            'acquirers': acquirers,
            'hostname': request.httprequest.url_root
        }
        html = request.env.ref('clouder_website_payment.payment_buttons').render(
            qweb_context,
            engine='ir.qweb',
            context=request.context
        )

        # Send response
        resp = {
            'clws_id': session.id,
            'html': html,
            'div_id': 'CL_payment',
            'js': [
                'clouder_website_payment/static/src/js/clouder_website_payment.js'
            ]
        }
        return request.make_response(json.dumps(resp), headers=HEADERS)

    @http.route('/clouder_form/payment_complete', type='http', auth='public', methods=['GET'])
    def payment_complete(self, **post):
        """
        Redirect page after a successful payment
        """
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        html = request.env.ref('clouder_website_payment.payment_success').render(
            {},
            engine='ir.qweb',
            context=request.context
        )

        return request.make_response(html, headers=HEADERS)

    @http.route('/clouder_form/payment_cancel', type='http', auth='public', methods=['GET'])
    def payment_cancel(self, **post):
        """
        Redirect page after a cancelled payment
        """
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        html = request.env.ref('clouder_website_payment.payment_cancel').render(
            {},
            engine='ir.qweb',
            context=request.context
        )

        return request.make_response(html, headers=HEADERS)

    @http.route('/clouder_form/payment_popup_wait', type='http', auth='public', methods=['GET'])
    def payment_cancel(self, **post):
        """
        Redirect page after a cancelled payment
        """
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        html = request.env.ref('clouder_website_payment.payment_popup').render(
            {},
            engine='ir.qweb',
            context=request.context
        )

        return request.make_response(html, headers=HEADERS)

    @http.route('/clouder_form/submit_acquirer', type='http', auth='public', methods=['POST'])
    def submit_acquirer(self, **post):
        """
        Fetches and returns the HTML base form
        """
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        if 'clws_id' not in post or 'acquirer_id' not in post:
            return self.bad_request("Bad request")
        else:
            post['clws_id'] = int(post['clws_id'])
            post['acquirer_id'] = int(post['acquirer_id'])

        orm_clws = request.env['clouder.web.session'].sudo()
        session = orm_clws.browse([post['clws_id']])[0]
        company = request.env.ref('base.main_company')

        # Make the payment transaction
        orm_paytr = request.env['payment.transaction'].sudo()
        orm_paytr.create({
            'acquirer_id': post['acquirer_id'],
            'type': 'form',
            'amount': session.amount,
            'currency_id': company.currency_id.id,
            'partner_id': session.partner_id.id,
            'partner_country_id': session.partner_id.country_id.id,
            'reference': session.reference,
        })

        html = request.env.ref('clouder_website_payment.payment_form_popup_message').render(
            {},
            engine='ir.qweb',
            context=request.context
        )

        resp = {
            'html': html,
            'js': [],
            'div_id': 'CL_payment_popup'
        }

        return request.make_response(json.dumps(resp), headers=HEADERS)
