from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest
from werkzeug.wsgi import ClosingIterator, wrap_file
from xmlrpclib import ServerProxy
import os
import json

SERVER = 'http://localhost:8069'
USERNAME = 'clouder_web_helper'
PASSWORD = 'clwh'


def serv_connect(database):
    server = ServerProxy('http://localhost:8069/xmlrpc/common')
    return server.login(database, USERNAME, PASSWORD)


def check_login(database, login, password=False):
    if not password:
        user_id = serv_connect(database)
        server = ServerProxy('http://localhost:8069/xmlrpc/object')
        return server.execute_kw(
            database, user_id, PASSWORD,
            'clouder.web.helper', 'check_login_exists', [login], {'context': {}}
        )
    else:
        server = ServerProxy('http://localhost:8069/xmlrpc/common')
        return server.login(database, login, password)


def call_html(database, lang):
    user_id = serv_connect(database)
    server = ServerProxy('http://localhost:8069/xmlrpc/object')
    return server.execute_kw(
        database, user_id, PASSWORD,
        'clouder.web.helper', 'get_form_html', [], {'context': {'lang': lang}}
    )


def process_form(database, data):
    user_id = serv_connect(database)
    server = ServerProxy('http://localhost:8069/xmlrpc/object')
    return server.execute_kw(
        database, user_id, PASSWORD,
        'clouder.web.helper', 'submit_form', [data], {'context': {'lang': data['lang']}}
    )


def load_env_from_partner(database, uid, lang):
    user_id = serv_connect(database)
    server = ServerProxy('http://localhost:8069/xmlrpc/object')
    return server.execute_kw(
        database, user_id, PASSWORD,
        'clouder.web.helper', 'get_env_ids', [uid], {'context': {'lang': lang}}
    )


class WSGIClouderForm(object):

    def __init__(self):
        self.env = None
        self.st_res = None

    def send_response(self, response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response(self.env, self.st_res)

    def request_form(self):
        req = Request(self.env)
        if 'db' not in req.form:
            raise BadRequest(description="Missing parameter")
        full_file = call_html(req.form['db'], req.form['lang'])
        return self.send_response(Response(full_file))

    def submit_form(self):
        req = Request(self.env)
        post_data = {x: req.form[x] for x in req.form}

        if 'db' not in post_data:
            raise BadRequest(description="Missing parameter")

        # Changing empty/missing env info into booleans
        if 'env_id' not in post_data or not post_data['env_id']:
            post_data['env_id'] = False
        if 'env_prefix' not in post_data or not post_data['env_prefix']:
            post_data['env_prefix'] = False

        result = process_form(post_data['db'], post_data)
        if int(result['code']):
            raise BadRequest(description=result['msg'])
        return self.send_response(Response(result['msg']))

    def plugin_js(self):
        js_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'plugin.js')
        js_fd = open(js_path)
        r = Response(wrap_file(self.env, js_fd), direct_passthrough=True)
        return self.send_response(r)

    def page_login(self):
        req = Request(self.env)
        post_data = {x: req.form[x] for x in req.form}
        if 'db' not in post_data or 'login' not in post_data:
            raise BadRequest(description="Missing parameter")
        if 'password' not in post_data:
            post_data['password'] = False
        result = bool(check_login(post_data['db'], post_data['login'], post_data['password']))
        return self.send_response(Response(json.dumps({'result': result})))

    def loading_gif(self):
        data = open('loading32x32.gif', 'rb').read()
        self.st_res('200 OK', [
            ('content-type', 'image/gif'),
            ('content-length', str(len(data))),
            ('Access-Control-Allow-Origin', '*')
        ])
        return [data]

    def get_env(self):
        req = Request(self.env)
        post_data = {x: req.form[x] for x in req.form}
        if 'db' not in post_data or 'login' not in post_data or 'password' not in post_data:
            raise BadRequest(description="Missing parameter")
        uid = check_login(post_data['db'], post_data['login'], post_data['password'])
        if not uid:
            return json.dumps({'error': 'Could not login with given credentials.'})
        result = load_env_from_partner(post_data['db'], uid, post_data['lang'])
        return self.send_response(Response(json.dumps({'result': result})))

    def __call__(self, environ, start_response):
        try:
            self.env = environ
            self.st_res = start_response
            request_url = environ['PATH_INFO']
            if request_url == '/request_form':
                return self.request_form()
            elif request_url == '/submit_form':
                return self.submit_form()
            elif request_url == '/plugin.js':
                return self.plugin_js()
            elif request_url == '/login':
                return self.page_login()
            elif request_url == '/img/loading32x32.gif':
                return self.loading_gif()
            elif request_url == '/get_env':
                return self.get_env()
            else:
                raise NotFound()
        except HTTPException, e:
            return ClosingIterator(self.send_response(e.get_response(self.env)))

if __name__ == '__main__':
    run_simple('0.0.0.0', 8065, WSGIClouderForm(), use_debugger=False, use_reloader=False)
