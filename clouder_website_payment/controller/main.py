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
        orm_inv = request.env['account.invoice'].sudo()
        orm_acq = request.env['payment.acquirer'].sudo()
        orm_cpny = request.env['res.company'].sudo()

        session = orm_clws.browse([data['result']['clws_id']])[0]
        company_id = orm_cpny._company_default_get('res.partner')

        # Creating invoice
        invoice_data = {
            'amount': session.application_id.pricegrid_ids.invoice_amount(),
            'partner_id': session.partner_id.id,
            'account_id': session.partner_id.property_account_receivable.id,
            'product_id': session.application_id.invoicing_product_id,
            'origin': session.application_id.name + "_" + fields.Date.today()
        }
        invoice_id = orm_inv.clouder_make_invoice(invoice_data)
        invoice = orm_inv.browse([invoice_id])[0]

        # Saving invoice reference
        session.write({'reference': invoice.internal_number})

        # Setting acquirer buttons
        acquirers = []
        render_ctx = dict(request.context, submit_class='btn btn-primary', submit_txt=_('Pay Now'))
        for acquirer in orm_acq.search([('website_published', '=', True), ('company_id', '=', company_id)]):
            acquirer.button = acquirer.with_context(**render_ctx).render(
                session.reference,
                invoice.amount_total,
                invoice.currency_id,
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

    @http.route('/clouder_form/payment_complete', type='http', auth='public', methods=['POST'])
    def payment_complete(self, **post):
        """
        Redirect page after a successful payment
        """
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        # TODO: remove debug
        import pprint
        _logger.info(u"\n\n{0}\n\n".format(pprint.pformat(post, indent=4)))

        html = request.env.ref('clouder_website_payment.payment_success').render(
            {},
            engine='ir.qweb',
            context=request.context
        )

        return request.make_response(html, headers=HEADERS)


    @http.route('/clouder_form/payment_cancel', type='http', auth='public', methods=['POST'])
    def payment_cancel(self, **post):
        """
        Redirect page after a cancelled payment
        """
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        # TODO: remove debug
        import pprint
        _logger.info(u"\n\n{0}\n\n".format(pprint.pformat(post, indent=4)))

        html = request.env.ref('clouder_website_payment.payment_cancel').render(
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

        request.env = request.env.with_context()

        if 'clws_id' not in post or 'acquirer_id' not in post:
            return self.bad_request("Bad request")
        else:
            post['clws_id'] = int(post['clws_id'])
            post['acquirer_id'] = int(post['acquirer_id'])

        orm_clws = request.env['clouder.web.session'].sudo()
        session = orm_clws.browse([post['clws_id']])[0]

        # Search the invoice
        orm_inv = request.env['account.invoice'].sudo()
        invoice = orm_inv.search([('internal_number', '=', session.reference)])
        if not invoice:
            # TODO: handle error here
            pass
        else:
            invoice = invoice[0]

        # Make the payment transaction
        orm_paytr = request.env['payment.transaction'].sudo()
        orm_paytr.create({
            'acquirer_id': post['acquirer_id'],
            'type': 'form',
            'amount': invoice.amount_total,
            'currency_id': invoice.currency_id,
            'partner_id': session.partner_id.id,
            'partner_country_id': session.partner_id.country_id.id,
            'reference': session.reference,
        })

        return request.make_response("OK", headers=HEADERS)
