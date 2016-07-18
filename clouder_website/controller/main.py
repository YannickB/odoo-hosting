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

from openerp import http, api, _
from openerp.http import request
from werkzeug.exceptions import HTTPException, NotFound, BadRequest
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file, ClosingIterator
from xmlrpclib import ServerProxy
import json
import logging
import copy
import os

_logger = logging.getLogger(__name__)

HEADERS = [('Access-Control-Allow-Origin', '*')]


class FormController(http.Controller):
    """
    HTTP controller to exchange with the external instance submission form
    """
    #######################
    #      Utilities      #
    #######################
    def env_with_context(self, context):
        """
        Returns a new environment made from the current request one and the given parameters
        """
        new_context = {k: v for k, v in request.context.iteritems()}
        new_context.update(context)
        return api.Environment(request.cr, request.uid, new_context)


    def check_login(self, login, password=False):
        """
        Checks the login
        If no password is provided, returns true if the login exists, false otherwise
        If a password is provided, returns true if the login/password are valid credentials, false otherwise
        """
        if not password:
            orm_clwh = request.env['clouder.web.helper'].sudo()
            return orm_clwh.check_login_exists(login)
        else:
            server = ServerProxy('http://localhost:8069/xmlrpc/common')
            return server.login(request.db, login, password)

    def bad_request(self, desc):
        """
        Returns a "Bad Request" response with CORS headers
        """
        _logger.warning('Bad request received: {0}'.format(desc))
        response = BadRequest(description=desc).get_response(request.httprequest.environ)
        for (hdr, val) in HEADERS:
            response.headers.add(hdr, val)
        return response

    def hook_next(self, data):
        """
        This function is meant to be overwritten by inheriting plugins
        """
        # Since there's nothing else to do in the original plugin, we just launch the instance creation
        orm_app = request.env['clouder.application'].sudo()
        instance_id = orm_app.create_instance_from_request(data['result']['clws_id'])

        resp = {
            'html': '',
            'div_id': '',
            'js': [],
            'clws_id': data['result']['clws_id']
        }

        if not instance_id:
            resp['html'] = """<p>""" + _("Error: instance creation failed.") + u"""</p>"""
            resp['div_id'] = 'CL_error_retry'
        else:
            resp['html'] = """<p>""" + \
                _("Your request for a Clouder instance has been sent.") + u"""<br/>""" + \
                _("Thank you for your interest in Clouder!") + u"""</p>"""
            resp['div_id'] = 'CL_final_thanks'

        return request.make_response(json.dumps(resp), headers=HEADERS)

    #######################
    #        Pages        #
    #######################
    @http.route('/clouder_form/request_form', type='http', auth='public', methods=['POST'])
    def request_form(self, **post):
        """
        Fetches and returns the HTML base form
        """
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        orm_clwh = request.env['clouder.web.helper'].sudo()
        full_file = orm_clwh.get_form_html()

        return request.make_response(full_file, headers=HEADERS)

    @http.route('/clouder_form/submit_form', type='http', auth='public', methods=['POST'])
    def submit_form(self, **post):
        """
        Submits the base form then calls the next part of the process
        """
        # Changing empty/missing env info into booleans
        if 'env_id' not in post or not post['env_id']:
            post['env_id'] = False
        if 'env_prefix' not in post or not post['env_prefix']:
            post['env_prefix'] = False
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        request.env = self.env_with_context({'lang': lang})

        orm_clwh = request.env['clouder.web.helper'].sudo()
        result = orm_clwh.submit_form(post)

        # Return bad request on failure
        if int(result['code']):
            return self.bad_request(result['msg'])

        data = {
            'post_data': {},
            'result': result
        }
        for x in post:
            data['post_data'][x] = copy.deepcopy(post[x])

        # Otherwise, we continue with the process
        return self.hook_next(data)

    @http.route('/clouder_form/check_data', type='http', auth='public', methods=['POST'])
    def check_data(self, **post):
        """
        Checks that the form data submitted is not a doublon
        """
        if 'inst_type' not in post:
            result = {'error': _('Missing inst_type parameter')}
            return request.make_response(json.dumps(result), headers=HEADERS)
        if post['inst_type'] not in ['container', 'base']:
            result = {'error': _('Incorrect inst_type parameter: {0}').format(post['inst_type'])}
            return request.make_response(json.dumps(result), headers=HEADERS)

        # Checking data errors for container requests
        if post['inst_type'] == 'container':
            if 'env_id' not in post or 'env_prefix' not in post or 'prefix' not in post:
                result = {'error': _('Missing argument for check.')}
                return request.make_response(json.dumps(result), headers=HEADERS)
            if post['env_id']:
                orm_cont = request.env['clouder.container'].sudo()
                # Searching for existing containers with the environment and prefix
                result = orm_cont.search([
                    ('environment_id', '=', int(post['env_id'])),
                    ('suffix', '=', post['prefix'])
                ])
                # If a container is found, return an error for those fields
                if result:
                    result = {
                        'next_step_validated': False,
                        'prefix': False,
                        'env_id': False,
                        'message': _('Container prefix already un use for this environment.') +
                        _('<br/>Please change the environment or prefix.')
                    }
                    return request.make_response(json.dumps(result), headers=HEADERS)

                # Otherwise, search for sessions that already reserved the name
                orm_clws = request.env['clouder.web.session'].sudo()
                result = orm_clws.search([
                    ('environment_id', '=', int(post['env_id'])),
                    ('prefix', '=', post['prefix'])
                ])
                # If there is such a session, invalidate data
                if result:
                    result = {
                        'next_step_validated': False,
                        'prefix': False,
                        'env_id': False,
                        'message': _('Container prefix already reserved for this environment.') +
                        _('<br/>Please change the environment or prefix.')
                    }
                    return request.make_response(json.dumps(result), headers=HEADERS)

                # No problem detected
                result = {
                    'next_step_validated': True,
                    'prefix': True,
                    'env_id': True,
                    'message': False
                }
                return request.make_response(json.dumps(result), headers=HEADERS)

            else:
                # Check that the environment prefix is not already attributed
                orm_env = request.env['clouder.environment'].sudo()
                result = orm_env.search([('prefix', '=', post['env_prefix'])])
                if result:
                    result = {
                        'env_prefix': result,
                        'message': _('Environment prefix already in use.') +
                        _('<br/>Please use a different environment or environment prefix.')
                    }
                    return request.make_response(json.dumps(result), headers=HEADERS)

                # Check that the environment prefix is not already reserved
                orm_clws = request.env['clouder.web.session'].sudo()
                result = orm_clws.search([
                    ('environment_id', '=', False),
                    ('env_prefix', '=', post['env_prefix'])
                ])
                if result:
                    result = {
                        'env_prefix': result,
                        'message': _('Environment prefix already reserved.') +
                        _('<br/>Please use a different environment or environment prefix.')
                    }
                    return request.make_response(json.dumps(result), headers=HEADERS)

                # No problem detected
                result = {
                    'next_step_validated': True,
                    'env_prefix': True,
                    'message': False
                }
                return request.make_response(json.dumps(result), headers=HEADERS)

        # Check data for base request
        elif post['inst_type'] == 'base':
            if 'domain_id' not in post or 'prefix' not in post:
                result = {'error': _('Missing argument for check.')}
                return request.make_response(json.dumps(result), headers=HEADERS)

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
                    'message': _('Base prefix is already in use for this domain.') +
                        _('<br/>Please change the prefix or domain.')
                }
                return request.make_response(json.dumps(result), headers=HEADERS)

            # Check that the prefix/domain combination is not already reserved
            orm_clws = request.env['clouder.web.session'].sudo()
            result = orm_clws.search([
                ('domain_id', '=', int(post['domain_id'])),
                ('prefix', '=', post['prefix'])
            ])

            if result:
                result = {
                    'next_step_validated': False,
                    'domain_id': False,
                    'prefix': False,
                    'message': _('Base prefix is already in reserved for this domain.') +
                        _('<br/>Please change the prefix or domain.')
                }
                return request.make_response(json.dumps(result), headers=HEADERS)

            # No problem detected
            result = {
                'next_step_validated': True,
                'domain_id': True,
                'prefix': True,
                'message': False
            }
            return request.make_response(json.dumps(result), headers=HEADERS)

    @http.route('/clouder_form/form_login', type='http', auth='public', methods=['POST'])
    def page_login(self, **post):
        """
        Uses check_login on the provided login and password
        See check_login docstring.
        """
        if 'login' not in post:
            return self.bad_request("Missing parameter login")
        if 'password' not in post:
            post['password'] = False
        result = self.check_login(post['login'], post['password'])
        return request.make_response(json.dumps({'result': result}), headers=HEADERS)

    @http.route('/clouder_form/get_env', type='http', auth='public', methods=['POST'])
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
            return json.dumps({'error': 'Could not login with given credentials.'})

        orm_clwh = request.env['clouder.web.helper'].sudo().with_context(lang=lang)
        result = orm_clwh.get_env_ids(uid)
        return request.make_response(json.dumps({'result': result}), headers=HEADERS)

    #######################
    #        Files        #
    #######################
    @http.route('/clouder_form/js/plugin.js', type='http', auth='public', methods=['GET'])
    def plugin_js(self, **post):
        """
        Serves the initial javascript plugin that makes the form work
        """
        current_dir = os.path.dirname(os.path.realpath(__file__))
        js_path = os.path.join(current_dir, '../static/src/js/plugin.js')
        js_fd = open(js_path)

        response = Response(
            wrap_file(request.httprequest.environ, js_fd),
            headers=HEADERS,
            direct_passthrough=True
        )
        return response

    @http.route('/clouder_form/img/loading32x32.gif', type='http', auth='public', methods=['GET'])
    def loading_gif(self, **post):
        """
        Serves the loading gif for the form
        """
        current_dir = os.path.dirname(os.path.realpath(__file__))
        gif_path = os.path.join(current_dir, '../static/src/img/loading32x32.gif')
        gif_data = open(gif_path)

        headers = [
            ('content-type', 'image/gif'),
            ('Access-Control-Allow-Origin', '*')
        ]

        response = Response(
            wrap_file(request.httprequest.environ, gif_data),
            headers=headers,
            direct_passthrough=True
        )
        return response
