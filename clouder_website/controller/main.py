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

from openerp import http
from openerp.http import request
from werkzeug.exceptions import HTTPException, NotFound, BadRequest
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file, ClosingIterator
from xmlrpclib import ServerProxy
import json
import logging
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
    def check_login(self, login, password=False):
        if not password:
            orm_clwh = request.env['clouder.web.helper'].sudo()
            return orm_clwh.check_login_exists(login)
        else:
            server = ServerProxy('http://localhost:8069/xmlrpc/common')
            return server.login(request.db, login, password)

    def bad_request(self, desc):
        response = BadRequest(description=desc).get_response(request.httprequest.environ)
        for header in HEADERS:
            response.headers.add(header)
        return response

    #######################
    #        Pages        #
    #######################
    @http.route('/request_form', type='http', auth='public', methods=['POST'])
    def request_form(self, **post):
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']

        orm_clwh = request.env['clouder.web.helper'].sudo().with_context(lang=lang)
        full_file = orm_clwh.get_form_html()

        return request.make_response(full_file, headers=HEADERS)

    @http.route('/submit_form', type='http', auth='public', methods=['POST'])
    def submit_form(self, **post):
        # Changing empty/missing env info into booleans
        if 'env_id' not in post or not post['env_id']:
            post['env_id'] = False
        if 'env_prefix' not in post or not post['env_prefix']:
            post['env_prefix'] = False
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']

        orm_clwh = request.env['clouder.web.helper'].sudo().with_context(lang=lang)
        result = orm_clwh.submit_form(post)

        # TODO: move those lines to a separate payment plugin
        # If there is no payment, launch the rest before returning to the client
        # if 'payment' in result and not result['payment']:
        #     result = orm_clwh.submit_payment(result['session_id'], True)

        # Return bad request on failure
        if int(result['code']):
            return self.bad_request(result['msg'])

        # Return a javascript-readable result on success
        return request.make_response(json.dumps(result), headers=HEADERS)

    @http.route('/form_login', type='http', auth='public', methods=['POST'])
    def page_login(self, **post):
        if 'login' not in post:
            return self.bad_request("Missing parameter")
        if 'password' not in post:
            post['password'] = False
        result = self.check_login(post['login'], post['password'])
        return request.make_response(json.dumps({'result': result}), headers=HEADERS)

    @http.route('/get_env', type='http', auth='public', methods=['POST'])
    def get_env(self, **post):
        # Check parameters
        lang = 'en_US'
        if 'lang' in post:
            lang = post['lang']
        if 'login' not in post or 'password' not in post:
            return self.bad_request("Missing parameter")

        uid = self.check_login(post['login'], post['password'])
        if not uid:
            return json.dumps({'error': 'Could not login with given credentials.'})

        orm_clwh = request.env['clouder.web.helper'].sudo().with_context(lang=lang)
        result = orm_clwh.get_env_ids(uid)
        return request.make_response(json.dumps({'result': result}), headers=HEADERS)

    #######################
    #        Files        #
    #######################
    @http.route('/js/plugin.js', type='http', auth='public', methods=['GET'])
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

    @http.route('/img/loading32x32.gif', type='http', auth='public', methods=['GET'])
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
