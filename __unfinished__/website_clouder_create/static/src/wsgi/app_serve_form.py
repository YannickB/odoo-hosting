from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest
from werkzeug.wsgi import ClosingIterator
from xmlrpclib import ServerProxy

SERVER = 'http://localhost:8069'
USERNAME = 'clouder_web_helper'
PASSWORD = 'clwh'


def serv_connect(database):
    server = ServerProxy('http://localhost:8069/xmlrpc/common')
    return server.login(database, USERNAME, PASSWORD)


def call_html(database, lang):
    user_id = serv_connect(database)
    server = ServerProxy('http://localhost:8069/xmlrpc/object')
    return server.execute_kw(
        database, user_id, PASSWORD,
        'clouder.web.helper', 'get_form_html', [], {'lang': lang}
    )


def process_form(database, data):
    user_id = serv_connect(database)
    server = ServerProxy('http://localhost:8069/xmlrpc/object')
    return server.execute(
        database, user_id, PASSWORD,
        'clouder.web.helper', 'submit_form', [data]
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
        result = process_form(post_data['db'], post_data)
        if int(result['code']):
            raise BadRequest(description=result['msg'])
        return self.send_response(Response(result['msg']))

    def __call__(self, environ, start_response):
        try:
            self.env = environ
            self.st_res = start_response
            request_url = environ['PATH_INFO']
            if request_url == '/request_form':
                return self.request_form()
            elif request_url == '/submit_form':
                return self.submit_form()
            else:
                raise NotFound()
        except HTTPException, e:
            return ClosingIterator(self.send_response(e.get_response(self.env)))

if __name__ == '__main__':
    run_simple('0.0.0.0', 8065, WSGIClouderForm(), use_debugger=False, use_reloader=True)
