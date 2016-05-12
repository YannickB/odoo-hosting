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

from openerp import models, fields, api, http, SUPERUSER_ID, _
from openerp.http import request

import logging

_logger = logging.getLogger(__name__)


class ClouderContainer(models.Model):
    """
    Adds the creation function to the container
    """

    _inherit = 'clouder.container'

    def create_instance(self, data):
        """
        Creates a clouder container or base using provided data
        """
        # TODO: implement
        _logger.info("\n\nCREATE INSTANCE DATA: {0}\n\n".format(data))

        # TODO: return newly created model
        return 0


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
        "country_id",
    ]

    other_mandatory_fields = [
        'application_id'
    ]

    partner_optionnal_fields = [
        "street",
        "zip",
        "state_id"
    ]

    def create_form_validate(self, data):
        """
        Checks that the necessary values are filled correctly
        """
        # Validation
        error = dict()
        for field_name in self.partner_mandatory_fields + self.other_mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        return error

    @http.route(['/instance/new'], type='http', auth="public", website=True)
    def display_new_form(self, **post):
        """
        Displays the web form to create a new instance
        """
        values = self.form_values()

        return request.render("website_clouder_create.create_form", values)

    @http.route('/instance/new/validate', type='http', auth="public", website=True)
    def instance_new_form_validate(self, **post):
        """
        Validates data and launches the instance creation process
        """
        # Check that the form is correct
        values = self.form_values(post)
        values['error'] = self.create_form_validate(values['form_data'])
        # Return to the first form on error
        if values['error']:
            return request.render("website_clouder_create.create_form", values)

        # Create partner
        values['partner_id'] = self.instance_form_save(values['form_data'])

        res = request.env['clouder.container'].create_instance({
            # TODO: fill in required vals
        })

        return request.render("website_clouder_create.create_validation", {'res': res})

    def instance_form_save(self, data):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')

        partner_lang = request.lang if request.lang in [lang.code for lang in request.website.language_ids] else None

        partner_info = {'customer': True}
        if partner_lang:
            partner_info['lang'] = partner_lang
        partner_info.update(self.parse_partner_fields(data))

        # set partner_id
        partner_id = None
        if uid != request.website.user_id.id:
            partner_id = orm_user.browse(cr, SUPERUSER_ID, uid, context=context).partner_id.id

        # save partner informations
        if partner_id and request.website.partner_id.id != partner_id:
            orm_partner.write(cr, SUPERUSER_ID, [partner_id], partner_info, context=context)
        else:
            # create partner
            partner_id = orm_partner.create(cr, SUPERUSER_ID, partner_info, context=context)

        if not isinstance(partner_id, int):
            partner_id = partner_id.id

        return partner_id

    def parse_partner_fields(self, data):
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

    def form_values(self, data=None):
        """
        Parses the values used in the form
        If data is not provided, creates default values for the form
        """
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        orm_user = registry.get('res.users')
        orm_country = registry.get('res.country')
        state_orm = registry.get('res.country.state')

        country_ids = orm_country.search(cr, SUPERUSER_ID, [], context=context)
        countries = orm_country.browse(cr, SUPERUSER_ID, country_ids, context)
        states_ids = state_orm.search(cr, SUPERUSER_ID, [], context=context)
        states = state_orm.browse(cr, SUPERUSER_ID, states_ids, context)
        partner = orm_user.browse(cr, SUPERUSER_ID, request.uid, context).partner_id
        applications = request.env['clouder.application'].search(
            [('web_create_type', '!=', 'disabled')]
        )

        form_data = {}
        if not data:
            if request.uid != request.website.user_id.id:
                form_data.update(self.parse_partner_fields(partner))
                form_data['application_id'] = ''
        else:
            form_data = self.parse_partner_fields(data)
            form_data['application_id'] = data.get('application_id', '')

        # Default search by user country
        if not form_data.get('country_id'):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country_ids = request.registry.get('res.country').search(
                    cr,
                    uid,
                    [('code', '=', country_code)],
                    context=context
                )
                if country_ids:
                    form_data['country_id'] = country_ids[0]

        values = {
            'countries': countries,
            'states': states,
            'form_data': form_data,
            'applications': applications,
            'error': {}
        }

        return values