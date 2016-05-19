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

from openerp import models, fields, api, http, _
from openerp.http import request

import logging

_logger = logging.getLogger(__name__)


class ClouderApplication(models.Model):
    """
    Adds information for web-creation on applications
    """

    _inherit = 'clouder.application'

    web_create_type = fields.Selection(
        [
            ('disabled', 'Disabled'),
            ('container', 'Container'),
            ('base', 'Base')
        ],
        'Web creation',
        default='disabled'
    )

    @api.multi
    def create_instance_from_request(self, data):
        """
        Creates a clouder container or base using provided data
        """
        # TODO: implement
        _logger.info("\n\nCREATE INSTANCE DATA: {0}\n\n".format(data))

        # TODO: return newly created model
        return 0


class ClouderWebHelper(models.Model):
    """
    A class made to be called by widgets and webpages alike
    """
    _name = 'clouder.web.helper'

    @api.multi
    def application_form_values(self, data=None):
        """
        Parses the values used in the form
        If data is not provided, creates default values for the form
        """
        app_orm = self.env['clouder.application'].sudo()
        domain_orm = self.env['clouder.domain'].sudo()
        applications = app_orm.search([('web_create_type', '!=', 'disabled')])
        domains = domain_orm.search([])

        application_id = ''
        application_name = ''
        domain_id = ''
        domain_name = ''
        prefix = ''

        if data:
            application_id = data.get('application_id', '')
            if application_id:
                application_id = int(application_id)
                application_name = app_orm.browse(application_id)['name']
            domain_id = data.get('domain_id', '')
            if domain_id:
                domain_id = int(domain_id)
                domain_name = domain_orm.browse(domain_id)['name']
            prefix = data.get('prefix', '')


        values = {
            'applications': applications,
            'domains': domains,
            'form_data': {
                'application_id': application_id,
                'prefix': prefix,
                'domain_id': domain_id,
                'application_name': application_name,
                'domain_name': domain_name
            },
            'error': {}
        }

        return values


class WebsiteClouderCreate(http.Controller):
    """
    Defines a webpage to request creation of clouder container/bases
    """

    partner_mandatory_fields = [
        "name",
        "phone",
        "email",
        "street2",
        "city",
        "country_id"
    ]
    partner_optionnal_fields = [
        "street",
        "zip",
        "state_id"
    ]

    app_mandatory_fields = [
        'application_id',
        'domain_id',
        'prefix'
    ]

    def instance_partner_save(self, data):
        """
        Saves the contact form data into a partner and returns the partner_id
            If an account was made, the corresponding partner is updated
        """
        orm_partner = request.env['res.partner'].sudo()
        orm_user = request.env['res.users'].sudo()

        partner_lang = request.lang if request.lang in [lang.code for lang in request.website.language_ids] else None

        partner_info = {'customer': True}
        if partner_lang:
            partner_info['lang'] = partner_lang
        partner_info.update(self.parse_partner_fields(data))

        # set partner_id
        partner_id = None
        partner = None
        if request.uid != request.website.user_id.id:
            partner = orm_user.browse(request.uid).partner_id
            partner_id = partner.id

        # save partner informations
        if partner_id and request.website.partner_id.id != partner_id:
            partner.write(partner_info)
        else:
            # create partner
            partner_id = orm_partner.create(partner_info)

        if not isinstance(partner_id, int):
            partner_id = partner_id.id

        return partner_id

    def parse_partner_fields(self, data):
        """
        Parses partner fields from form data
        """
        # set mandatory and optional fields
        partner_fields = self.partner_mandatory_fields + \
            self.partner_optionnal_fields

        # set data
        if isinstance(data, dict):
            query = dict((field_name, data[field_name])
                for field_name in partner_fields if field_name in data)
        else:
            query = dict((field_name, getattr(data, field_name))
                for field_name in partner_fields if getattr(data, field_name))
            if data.parent_id:
                query['street'] = data.parent_id.name

        if query.get('state_id'):
            query['state_id'] = int(query['state_id'])
        if query.get('country_id'):
            query['country_id'] = int(query['country_id'])

        return query

    def partner_form_values(self, data=None):
        """
        Parses the values used in the form
        If data is not provided, creates default values for the form
        """
        orm_user = request.env['res.users'].sudo()
        orm_country = request.env['res.country'].sudo()
        state_orm = request.env['res.country.state'].sudo()

        countries = orm_country.search([])
        states = state_orm.search([])
        partner = orm_user.browse(request.uid).partner_id

        form_data = {}
        if not data:
            if request.uid != request.website.user_id.id:
                form_data.update(self.parse_partner_fields(partner))
        else:
            form_data = self.parse_partner_fields(data)

        # Default search by user country
        if not form_data.get('country_id'):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country = orm_country.search([('code', '=', country_code)])
                if country:
                    form_data['country_id'] = country[0].id

        values = {
            'countries': countries,
            'states': states,
            'form_data': form_data,
            'error': {}
        }

        return values

    def application_form_validate(self, data):
        """
        Checks that the necessary values are filled correctly
        """
        # Validation
        error = dict()
        for field_name in self.app_mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        return error

    def partner_form_validate(self, data):
        """
        Checks that the necessary values are filled correctly
        """
        # Validation
        error = dict()
        for field_name in self.partner_mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        return error

    @http.route(['/instance/new'], type='http', auth="public", website=True)
    def display_app_form(self, **post):
        """
        Displays the web form to create a new instance
        """
        values = request.env['clouder.web.helper'].application_form_values()
        return request.render("website_clouder_create.create_app_form", values)

    @http.route(['/instance/new/contact_info'], type='http', auth="public", website=True)
    def display_partner_form(self, **post):
        """
        Displays the web form to create a new instance
        """
        # Check the returned values
        app_values = request.env['clouder.web.helper'].application_form_values(data=post)
        app_values['error'] = self.application_form_validate(app_values['form_data'])
        # Return to the first form on error
        if app_values['error']:
            return request.render("website_clouder_create.create_app_form", app_values)

        # Updating session
        request.session['first_form_values'] = app_values['form_data']

        # Display new form
        values = self.partner_form_values()
        return request.render("website_clouder_create.create_partner_form", values)

    @http.route('/instance/new/validate', type='http', auth="public", website=True)
    def instance_new_form_validate(self, **post):
        """
        Validates data and launches the instance creation process
        """
        # Check that the form is correct
        values = self.partner_form_values(post)
        values['error'] = self.partner_form_validate(values['form_data'])
        # Return to the first form on error
        if values['error']:
            return request.render("website_clouder_create.create_partner_form", values)

        # Create partner
        values['partner_id'] = self.instance_partner_save(values['form_data'])

        # TODO: fill in required vals
        res = request.env['clouder.application'].sudo().create_instance_from_request([])

        final_vals = {
            'res': res,
            'app_name': request.session['first_form_values']['application_name'],
            'domain_name':
                request.session['first_form_values']['prefix'] + '.' +
                request.session['first_form_values']['domain_name']
        }

        return request.render("website_clouder_create.create_validation", final_vals)
