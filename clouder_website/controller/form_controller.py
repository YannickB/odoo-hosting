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

try:
    from odoo import http, api, _
    from odoo.http import request
except ImportError:
    from openerp import http, api, _
    from openerp.http import request

from werkzeug.wsgi import wrap_file
from werkzeug.wrappers import Response
from xmlrpclib import ServerProxy
from unicodedata import normalize
import os
import json
import logging
import copy

_logger = logging.getLogger(__name__)

HEADERS = [('Access-Control-Allow-Origin', '*')]


class FormController(http.Controller):
    """
    HTTP controller to exchange with the external instance submission form
    """
    #######################
    #      Utilities      #
    #######################
    @staticmethod
    def uni_norm(string):
        """
        Formats the passed string into its closest ascii form and returns it
        Used to transform accents into their unnaccented
        counterparts for sorting
        Example:
            uni_norm(u'àéèêÏÎç') returns 'aeeeIIc'
        """
        if not isinstance(string, unicode):
            return string
        return normalize('NFD', string).encode('ascii', 'ignore')

    def env_with_context(self, context):
        """
        Returns a new environment made from the current
        request one and the given parameters
        """
        new_context = {k: v for k, v in request.context.iteritems()}
        new_context.update(context)
        return api.Environment(request.cr, request.uid, new_context)

    def check_login(self, login, password=False):
        """
        Checks the login
        If no password is provided, returns true if the login exists,
        false otherwise
        If a password is provided, returns true if the login/password
        are valid credentials, false otherwise
        """
        if not password:
            orm_user = request.env['res.users'].sudo()
            return bool(orm_user.search([('login', '=', login)]))
        else:
            server = ServerProxy('http://localhost:8069/xmlrpc/common')
            return server.login(request.db, login, password)

    def bad_request(self, desc):
        """
        Returns a "Bad Request" response with CORS headers
        """
        # TODO: replace with error handling
        _logger.warning('Bad request received: {0}'.format(desc))
        response = {
            "error": desc
        }
        return request.make_response(json.dumps(response), headers=HEADERS)

    def hook_next(self, data):
        """
        This function is meant to be overwritten by inheriting plugins
        """
        # Since there's nothing else to do in the original plugin,
        # we just launch the instance creation
        orm_app = request.env['clouder.application'].sudo()
        instance_id = orm_app.create_instance_from_request(
            data['result']['clws_id'])

        resp = {
            'html': '',
            'div_id': '',
            'js': [],
            'clws_id': data['result']['clws_id']
        }

        if not instance_id:
            resp['html'] = """<p>""" + \
                           _("Error: instance creation failed.") + u"""</p>"""
            resp['div_id'] = 'CL_error_retry'
        else:
            resp['html'] = """<p>""" + \
                _("Your request for a Clouder instance has been sent.") \
                + u"""<br/>""" + \
                _("Thank you for your interest in Clouder!") + u"""</p>"""
            resp['div_id'] = 'CL_final_thanks'

        return request.make_response(json.dumps(resp), headers=HEADERS)

    #######################
    #        Files        #
    #######################
    @http.route('/clouder_form/fontawesome/<string:path>',
                type='http', auth='public', method=['GET'])
    def request_font_awesome(self, path, **post):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        ressource_path = os.path.join(
            current_dir,
            "../static/lib/fontawesome/fonts",
            path)
        response = Response(
            wrap_file(request.httprequest.environ, open(ressource_path)),
            headers=HEADERS,
            direct_passthrough=True
        )
        return response

    #######################
    #        Pages        #
    #######################
    @http.route(
        '/clouder_form/request_form', type='http',
        auth='public', methods=['POST'], csrf=False)
    def request_form(self, **post):
        """
        Generates and returns the HTML base form
        """
        # Check parameters
        if 'hostname' not in post or not post['hostname']:
            return self.bad_request(_("Missing argument hostname"))
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        # Getting data to generate the form
        app_orm = request.env['clouder.application'].sudo()
        domain_orm = request.env['clouder.domain'].sudo()
        country_orm = request.env['res.country'].sudo()
        state_orm = request.env['res.country.state'].sudo()

        applications = app_orm.search([('web_create_type', '!=', 'disabled')])
        domains = domain_orm.search([])
        countries = country_orm.search([])
        states = state_orm.search([])

        font_awesome = """
@font-face {
    font-family: 'FontAwesome';
    src: url('%(path)s.eot?v=4.2.0');
    src: url('%(path)s.eot?#iefix&v=4.2.0') format('embedded-opentype'),
         url('%(path)s.woff?v=4.2.0') format('woff'),
         url('%(path)s.ttf?v=4.2.0') format('truetype'),
         url('%(path)s.svg?v=4.2.0#fontawesomeregular') format('svg');
    font-weight: normal;
    font-style: normal;
}
        """ % {
            'path':
                post['hostname'].rstrip('/') +
                "/clouder_form/fontawesome/fontawesome-webfont",
        }

        # Render the form
        qweb_context = {
            'applications':
                applications.sorted(key=lambda r: self.uni_norm(r.name)),
            'domains': domains.sorted(key=lambda r: self.uni_norm(r.name)),
            'countries': countries.sorted(key=lambda r: self.uni_norm(r.name)),
            'states': states.sorted(key=lambda r: self.uni_norm(r.name)),
            'hostname': post['hostname'].rstrip('/'),
            'font_awesome_definition': font_awesome
        }
        html = request.env.ref('clouder_website.plugin_form').render(
            qweb_context,
            engine='ir.qweb',
            context=request.context
        )

        return request.make_response(html, headers=HEADERS)

    @http.route(
        '/clouder_form/tos', type='http',
        auth='public', methods=['GET'], csrf=False)
    def form_tos(self, **post):
        """
        Generates and returns the HTML TOS page
        """
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        html = request.env.ref('clouder_website.form_tos').render(
            {},
            engine='ir.qweb',
            context=request.context
        )

        return request.make_response(html, headers=HEADERS)

    @http.route(
        '/clouder_form/submit_form', type='http',
        auth='public', methods=['POST'], csrf=False)
    def submit_form(self, **post):
        """
        Submits the base form then calls the next part of the process
        """
        # Changing empty/missing env info into booleans
        if 'environment_id' not in post or not post['environment_id']:
            post['environment_id'] = False
        if 'environment_prefix' not in post or not post['environment_prefix']:
            post['environment_prefix'] = False
        if 'hostname' not in post or not post['hostname']:
            return self.bad_request(_("Missing argument hostname"))

        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

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
        instance_mandatory_fields = [
            'application_id',
            'clouder_partner_id'
        ]
        instance_optional_fields = [
            'suffix',
            'environment_id',
            'environment_prefix',
            'title',
            'domain_id',
            'prefix',
        ]
        other_fields = [
            'password'
        ]

        # Checking data
        partner_data = {}
        for mandat in partner_mandatory_fields:
            if mandat not in post or not post[mandat]:
                return self.bad_request('Missing field "{0}"'.format(mandat))

            # Make sure we only backup lower-case email adresses
            # to avoid mismatch when checking login
            if mandat == "email":
                post[mandat] = post[mandat].lower()

            partner_data[mandat] = post[mandat]
        for opt in partner_optionnal_fields:
            if opt in post:
                partner_data[opt] = post[opt]

        partner_data['country_id'] = int(partner_data['country_id'])
        if 'state_id' in partner_data and partner_data['state_id']:
            partner_data['state_id'] = int(partner_data['state_id'])

        instance_data = {}
        for mandat in instance_mandatory_fields:
            if mandat not in post or not post[mandat]:
                return self.bad_request('Missing field "{0}"'.format(mandat))
            instance_data[mandat] = post[mandat]

        for opt in instance_optional_fields:
            if opt in post:
                instance_data[opt] = post[opt]
            else:
                instance_data[opt] = False

        other_data = {}
        for opt in other_fields:
            if opt in post:
                other_data[opt] = post[opt]
            else:
                other_data[opt] = False

        # All data retrieved
        orm_partner = request.env['res.partner'].sudo()
        orm_user = request.env['res.users'].sudo()

        # If the user exists, try to login and update partner
        if self.check_login(partner_data['email']):
            # Check that the password exists and is correct
            user_id = False
            if other_data['password']:
                user_id = self.check_login(
                    partner_data['email'], other_data['password'])
            if not user_id:
                return self.bad_request('Incorrect user/password')

            # Retrieve user
            user = orm_user.browse([user_id])[0]

            # Do not update empty fields
            partner_update_dict = copy.deepcopy(partner_data)
            for x in partner_data:
                if not partner_update_dict[x]:
                    del partner_update_dict[x]

            user.partner_id.write(partner_update_dict)
            instance_data['partner_id'] = user.partner_id.id

        # If the user doesn't exist, create a new partner
        else:
            instance_data['partner_id'] = orm_partner.create(partner_data).id

        # Parsing instance data
        instance_data['clouder_partner_id'] = \
            int(instance_data['clouder_partner_id'])
        instance_data['application_id'] = int(instance_data['application_id'])
        if instance_data['domain_id']:
            instance_data['domain_id'] = int(instance_data['domain_id'])
        if instance_data['environment_id']:
            instance_data['environment_id'] = \
                int(instance_data['environment_id'])

        # Creating session using information
        orm_cws = request.env['clouder.web.session'].sudo()
        session_id = orm_cws.create(instance_data)

        data = {
            'post_data': {},
            'result': {
                'code': 0,
                'msg': 'Session created',
                'clws_id': session_id.id,
                'payment': False
            }
        }
        for x in post:
            data['post_data'][x] = copy.deepcopy(post[x])

        return self.hook_next(data)

    @http.route(
        '/clouder_form/check_data', type='http',
        auth='public', methods=['POST'], csrf=False)
    def check_data(self, **post):
        """
        Checks that the form data submitted is not a doublon
        """
        if 'inst_type' not in post:
            result = {'error': _('Missing inst_type parameter')}
            return request.make_response(json.dumps(result), headers=HEADERS)
        if post['inst_type'] not in ['service', 'base']:
            result = {
                'error': _('Incorrect inst_type parameter: {0}')
                .format(post['inst_type'])}
            return request.make_response(json.dumps(result), headers=HEADERS)

        # Checking data errors for service requests
        if post['inst_type'] == 'service':
            # Check that the required data has been passed
            if ('environment_id' not in post and
                    'environment_prefix' not in post) or \
                    'suffix' not in post:
                result = {
                    'error': _('Prefix and either environment_id or '
                               'environment_prefix are required.')}
                return \
                    request.make_response(json.dumps(result), headers=HEADERS)
            # Check that the required data is not empty
            if (not post['environment_id'] and
                    not post['environment_prefix']) or not post['suffix']:
                result = {
                    'error': _('Prefix and either environment_id or '
                               'environment_prefix should not be empty.')}
                return \
                    request.make_response(json.dumps(result), headers=HEADERS)

            # If we have an ID
            if post['environment_id']:
                # Check that the ID is valid
                try:
                    int(post['environment_id'])
                except ValueError:
                    result = {
                        'error': _('Invalid environment_id: {0}.')
                        .format(post['environment_id'])}
                    return request.make_response(
                        json.dumps(result), headers=HEADERS)

                orm_cont = request.env['clouder.service'].sudo()
                # Searching for existing services with
                # the environment and suffix
                result = orm_cont.search([
                    ('environment_id', '=', int(post['environment_id'])),
                    ('suffix', '=', post['suffix'])
                ])
                # If a service is found, return an error for those fields
                if result:
                    result = {
                        'next_step_validated': False,
                        'suffix': False,
                        'environment_id': False,
                        'message': _('Container name already un use '
                                     'for this environment.') +
                        _('<br/>Please change the environment or suffix.')
                    }
                    return request.make_response(
                        json.dumps(result), headers=HEADERS)

                # Otherwise, search for sessions that already reserved the name
                orm_clws = request.env['clouder.web.session'].sudo()
                result = orm_clws.search([
                    ('environment_id', '=', int(post['environment_id'])),
                    ('suffix', '=', post['suffix'])
                ])
                # If there is such a session, invalidate data
                if result:
                    result = {
                        'next_step_validated': False,
                        'suffix': False,
                        'environment_id': False,
                        'message': _('Container suffix already reserved '
                                     'for this environment.') +
                        _('<br/>Please change the environment or suffix.')
                    }
                    return request.make_response(
                        json.dumps(result), headers=HEADERS)

                # No problem detected
                result = {
                    'next_step_validated': True,
                    'suffix': True,
                    'environment_id': True,
                    'message': False
                }
                return request.make_response(
                    json.dumps(result), headers=HEADERS)

            else:
                # Check that the environment prefix is not already attributed
                orm_env = request.env['clouder.environment'].sudo()
                result = orm_env.search([
                    ('prefix', '=', post['environment_prefix'])])
                if result:
                    result = {
                        'environment_prefix': False,
                        'message': _('Environment prefix already in use.') +
                        _('<br/>Please use a different environment '
                          'or environment prefix.')
                    }
                    return request.make_response(
                        json.dumps(result), headers=HEADERS)

                # Check that the environment prefix is not already reserved
                orm_clws = request.env['clouder.web.session'].sudo()
                orm_app = request.env['clouder.application'].sudo()
                app_ids = [
                    app.id for app in orm_app.search([
                        ('web_create_type', '=', 'service')
                    ])
                ]

                result = orm_clws.search([
                    ('application_id', 'in', app_ids),
                    ('environment_id', '=', False),
                    ('environment_prefix', '=', post['environment_prefix'])
                ])
                if result:
                    result = {
                        'environment_prefix': False,
                        'message': _('Environment prefix already reserved.') +
                        _('<br/>Please use a different environment '
                          'or environment prefix.')
                    }
                    return request.make_response(
                        json.dumps(result), headers=HEADERS)

                # No problem detected
                result = {
                    'next_step_validated': True,
                    'environment_prefix': True,
                    'message': False
                }
                return request.make_response(
                    json.dumps(result), headers=HEADERS)

        # Check data for base request
        elif post['inst_type'] == 'base':
            if 'domain_id' not in post or 'prefix' not in post:
                result = {'error': _('Missing argument for check.')}
                return request.make_response(
                    json.dumps(result), headers=HEADERS)

            # Check that the prefix is not already in use for this domain
            orm_base = request.env['clouder.base'].sudo()
            result = orm_base.search([
                ('domain_id', '=', int(post['domain_id'])),
                ('name', '=', post['prefix'])
            ])
            if result:
                result = {
                    'next_step_validated': False,
                    'domain_id': False,
                    'prefix': False,
                    'message':
                        _('Base prefix is already in use for this domain.') +
                        _('<br/>Please change the prefix or domain.')
                }
                return request.make_response(
                    json.dumps(result), headers=HEADERS)

            # Check that the prefix/domain combination is not already reserved
            orm_clws = request.env['clouder.web.session'].sudo()
            orm_app = request.env['clouder.application'].sudo()

            app_ids = [
                app.id for app in orm_app.search([
                    ('web_create_type', '=', 'base')
                ])
            ]

            result = orm_clws.search([
                ('application_id', 'in', app_ids),
                ('domain_id', '=', int(post['domain_id'])),
                ('prefix', '=', post['prefix'])
            ])

            if result:
                result = {
                    'next_step_validated': False,
                    'domain_id': False,
                    'prefix': False,
                    'message':
                        _('Base prefix is already in '
                          'reserved for this domain.') +
                        _('<br/>Please change the prefix or domain.')
                }
                return request.make_response(
                    json.dumps(result), headers=HEADERS)

            # No problem detected
            result = {
                'next_step_validated': True,
                'domain_id': True,
                'prefix': True,
                'message': False
            }
            return request.make_response(json.dumps(result), headers=HEADERS)

    @http.route('/clouder_form/form_login', type='http',
                auth='public', methods=['POST'], csrf=False)
    def page_login(self, **post):
        """
        Uses check_login on the provided login and password
        See check_login docstring.
        """
        if 'login' not in post:
            return self.bad_request("Missing parameter login")
        if 'password' not in post:
            post['password'] = False
        uid = self.check_login(post['login'], post['password'])

        result = {'response': bool(uid)}

        # Provide information to fill the form if login was successfull
        if post['password'] and uid:
            orm_user = request.env['res.users'].sudo()
            user = orm_user.browse([uid])[0]

            result['partner_info'] = {
                "name": user.partner_id.name,
                "phone": user.partner_id.phone,
                "email": user.partner_id.email,
                "street2": user.partner_id.street2,
                "city": user.partner_id.city,
                "country_id": user.partner_id.country_id.id,
                "street": user.partner_id.street,
                "zip": user.partner_id.zip,
                "state_id": user.partner_id.state_id.id
            }

        return request.make_response(json.dumps(result), headers=HEADERS)

    @http.route('/clouder_form/get_env', type='http',
                auth='public', methods=['POST'], csrf=False)
    def get_env(self, **post):
        """
        Returns the list of environments linked to the given user
        Requires correct credentials (login/password) for the user
        """
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        if 'login' not in post or 'password' not in post:
            return self.bad_request("Missing credentials")

        uid = self.check_login(post['login'], post['password'])
        if not uid:
            return json.dumps(
                {'error': _('Could not login with given credentials.')})

        env_orm = request.env['clouder.environment'].sudo()
        user_orm = request.env['res.users'].sudo()

        user = user_orm.browse([uid])[0]
        env_ids = env_orm.search([('partner_id', '=', user.partner_id.id)])

        result = {}
        for env in env_ids:
            result[str(env.id)] = {
                'name': env.name
            }

        return request.make_response(
            json.dumps({'result': result}), headers=HEADERS)
