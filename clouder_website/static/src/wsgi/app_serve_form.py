from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import ClosingIterator, wrap_file
from werkzeug.exceptions import HTTPException, NotFound, BadRequest
from xmlrpclib import ServerProxy
import os
import json

SERVER = 'http://localhost:8069'
USERNAME = 'clouder_web_helper'
PASSWORD = 'clwh'


def serv_connect(database):
    server = ServerProxy('http://localhost:8069/xmlrpc/common')
    return server.login(database, USERNAME, PASSWORD)


def load_env_from_partner(database, uid, lang):
    user_id = serv_connect(database)
    server = ServerProxy('http://localhost:8069/xmlrpc/object')
    return server.execute_kw(
        database, user_id, PASSWORD,
        'clouder.web.helper', 'get_env_ids', [uid], {'context': {'lang': lang}}
    )


def call_payment(database, sess_id, payment, lang):
    user_id = serv_connect(database)
    server = ServerProxy('http://localhost:8069/xmlrpc/object')
    return server.execute_kw(
        database, user_id, PASSWORD,
        'clouder.web.helper', 'submit_payment', [sess_id, payment], {'context': {'lang': lang}}
    )


class WSGIClouderForm(object):

    def __init__(self):
        self.env = None
        self.st_res = None

    def send_response(self, response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response(self.env, self.st_res)

    def submit_payment(self):
        req = Request(self.env)
        post_data = {x: req.form[x] for x in req.form}

        if 'db' not in post_data or 'cl_id' not in post_data:
            raise BadRequest(description="Missing parameter")

    def __call__(self, environ, start_response):
        try:
            self.env = environ
            self.st_res = start_response
            request_url = environ['PATH_INFO']
            raise NotFound()
        except HTTPException, e:
            return ClosingIterator(self.send_response(e.get_response(self.env)))

if __name__ == '__main__':
    run_simple('0.0.0.0', 8065, WSGIClouderForm(), use_debugger=False, use_reloader=False)
