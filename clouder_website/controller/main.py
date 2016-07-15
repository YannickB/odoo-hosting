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
