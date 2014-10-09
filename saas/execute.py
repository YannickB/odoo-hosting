# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Buron
#    Copyright 2013 Yannick Buron
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

import time
from datetime import datetime, timedelta
import subprocess
import paramiko
import os.path
import string
import errno
import random

import logging
_logger = logging.getLogger(__name__)


class saas_log(osv.osv):
    _name = 'saas.log'

    def _get_name(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for log in self.browse(cr, uid, ids, context=context):
            model_obj = self.pool.get(log.model)
            record = model_obj.browse(cr, uid, log.res_id, context=context)
            res[log.id] = ''
            if record and hasattr(record, 'name'):
                res[log.id] = record.name
        return res

    _columns = {
        'model': fields.char('Related Document Model', size=128, select=1),
        'res_id': fields.integer('Related Document ID', select=1),
        'name': fields.function(_get_name, type="char", size=128, string='Name'),
        'action': fields.char('Action', size=64),
        'log': fields.text('log'),
        'state': fields.selection([('unfinished','Not finished'),('ok','Ok'),('ko','Ko')], 'State', required=True),
        'create_date': fields.datetime('Launch Date'),
        'finish_date': fields.datetime('Finish Date'),
        'expiration_date': fields.datetime('Expiration Date'),
    }

    _defaults = {
        'state': 'unfinished'
    }

    _order = 'create_date desc'

class saas_model(osv.AbstractModel):
    _name = 'saas.model'

    _log_expiration_days = 30

    _columns = {
        'log_ids': fields.one2many('saas.log', 'res_id',
            domain=lambda self: [('model', '=', self._name)],
            auto_join=True,
            string='Logs'),
    }

    def create_log(self, cr, uid, id, action, context):
        if 'log_id' in context:
            return context
        log_obj = self.pool.get('saas.log')
        if context == None:
            context = {}
        if not 'logs' in context:
            context['logs'] = {}
        if not self._name in context['logs']:
            context['logs'][self._name] = {}
        now = datetime.now()
        #_logger.info('start log model %s, res %s', self._name, id)
        if not id in context['logs'][self._name]:
            expiration_date = (now + timedelta(days=self._log_expiration_days)).strftime("%Y-%m-%d")
            log_id = log_obj.create(cr, uid, {'model': self._name, 'res_id': id, 'action': action,'expiration_date':expiration_date}, context=context)
            context['logs'][self._name][id] = {}
            context['logs'][self._name][id]['log_model'] = self._name
            context['logs'][self._name][id]['log_res_id'] = id
            context['logs'][self._name][id]['log_id'] = log_id
            context['logs'][self._name][id]['log_log'] = ''
        return context

    def end_log(self, cr, uid, id, context=None):
        log_obj = self.pool.get('saas.log')
        #_logger.info('end log model %s, res %s', self._name, id)
        if 'logs' in  context:
            log = log_obj.browse(cr, uid, context['logs'][self._name][id]['log_id'], context=context)
            if log.state == 'unfinished':
                log_obj.write(cr, uid, [context['logs'][self._name][id]['log_id']], {'state': 'ok'}, context=context)

    def deploy_links(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if hasattr(record, 'link_ids'):
                for link in record.link_ids:
                    vals = self.pool.get(link._name).get_vals(cr, uid, link.id, context=context)
                    self.pool.get(link._name).deploy(cr, uid, vals, context=context)

    def purge_links(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if hasattr(record, 'link_ids'):
                for link in record.link_ids:
                    vals = self.pool.get(link._name).get_vals(cr, uid, link.id, context=context)
                    self.pool.get(link._name).purge(cr, uid, vals, context=context)

    def reinstall(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            context = self.create_log(cr, uid, record.id, 'reinstall', context)
            vals = self.get_vals(cr, uid, record.id, context=context)
            self.purge_links(cr, uid, [record.id], context=context)
            self.purge(cr, uid, vals, context=context)
            self.deploy(cr, uid, vals, context=context)
            self.deploy_links(cr, uid, [record.id], context=context)
            self.end_log(cr, uid, record.id, context=context)

    def create(self, cr, uid, vals, context=None):
        res = super(saas_model, self).create(cr, uid, vals, context=context)
        context = self.create_log(cr, uid, res, 'create', context)
        vals = self.get_vals(cr, uid, res, context=context)
        try:
            self.deploy(cr, uid, vals, context)
            self.deploy_links(cr, uid, [res], context=context)
        except:
            log('===================', context)
            log('FAIL! Reverting...', context)
            log('===================', context)
            context['nosave'] = True
            self.unlink(cr, uid, [res], context=context)
            raise
        self.end_log(cr, uid, res, context=context)
        return res 

    def unlink(self, cr, uid, ids, context={}):
        for record in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, record.id, context=context)
            try:
                self.purge_links(cr, uid, [record.id], context=context)
                self.purge(cr, uid, vals, context=context)
            except:
                pass   
        res = super(saas_model, self).unlink(cr, uid, ids, context=context)
        #Security to prevent log to write in a removed saas.log
        for id in ids:
            if 'logs' in context and self._name in context['logs'] and id in context['logs'][self._name]:
                del context['logs'][self._name][id]
        log_obj = self.pool.get('saas.log')
        log_ids = log_obj.search(cr, uid, [('model','=',self._name),('res_id','in',ids)],context=context)
        log_obj.unlink(cr, uid, log_ids, context=context)
        return res


def log(message, context):
    message = filter(lambda x: x in string.printable, message)
    _logger.info(message)
    log_obj = context['saas-self'].pool.get('saas.log')
    if 'logs' in context:
        # _logger.info('context.log %s', context['logs'])
        for model, model_vals in context['logs'].iteritems():
            for res_id, vals in context['logs'][model].iteritems():
                log = log_obj.browse(context['saas-cr'], context['saas-uid'], context['logs'][model][res_id]['log_id'], context=context)
                log_obj.write(context['saas-cr'], context['saas-uid'], context['logs'][model][res_id]['log_id'], {'log': (log.log or '') + message + '\n'}, context=context)

def ko_log(self, context):
    log_obj = context['saas-self'].pool.get('saas.log')
    if 'logs' in context:
        for model, model_vals in context['logs'].iteritems():
            for res_id, vals in context['logs'][model].iteritems():
                log_obj.write(context['saas-cr'], context['saas-uid'], context['logs'][model][res_id]['log_id'], {'state': 'ko'}, context=context)


def connect(host, port=False, username=False, context={}):
    log('connect: ssh ' + (username and username + '@' or '') + host + (port and ' -p ' + str(port) or ''), context)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh_config = paramiko.SSHConfig()
    user_config_file = os.path.expanduser("~/.ssh/config")
    if os.path.exists(user_config_file):
        with open(user_config_file) as f:
            ssh_config.parse(f)
    user_config = ssh_config.lookup(host)

    identityfile = None
    if 'identityfile' in user_config:
        host = user_config['hostname']
        identityfile = user_config['identityfile']
        if not username:
            username = user_config['user']
        if not port:
            port = user_config['port']

    ssh.connect(host, port=int(port), username=username, key_filename=identityfile)
    sftp = ssh.open_sftp()
    return (ssh, sftp)

def execute(ssh, cmd, context, stdin_arg=False,path=False):
    log('command : ' + ' '.join(cmd), context)
    if path:
        log('path : ' + path, context)
        cmd.insert(0, 'cd ' + path + ';')
    stdin, stdout, stderr = ssh.exec_command(' '.join(cmd))
    if stdin_arg:
        for arg in stdin_arg:
            log('command : ' + arg, context)
            stdin.write(arg)
            stdin.flush()
#    _logger.info('stdin : %s', stdin.read())
    stdout_read = stdout.read()
    log('stdout : ' + stdout_read, context)
    log('stderr : ' + stderr.read(), context)
    return stdout_read


def send(sftp, source, destination, context):
    log('send : ' + source + ' to ' + destination, context)
    sftp.put(source, destination)

def execute_local(cmd, context, path=False, shell=False):
    log('command : ' + ' '.join(cmd), context)
    cwd = os.getcwd()
    if path:
        log('path : ' + path, context)
        os.chdir(path)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)
#    for line in proc.stdin:
#       line = 'stdin : ' + line
#       log(line, context=context)
    for line in proc.stdout:
       line = 'stdout : ' + line
       log(line, context)
#    for line in proc.stderr:
#       line = 'stderr : ' + line
#       log(line, context)
    os.chdir(cwd)
    return proc.stdout

def exist(sftp, path):
    try:
        sftp.stat(path)
    except IOError, e:
        if e.errno == errno.ENOENT:
            return False
        raise
    else:
        return True

def local_file_exist(file):
    return os.path.isfile(file)

def local_dir_exist(file):
    return os.path.isdir(file)

def execute_write_file(file, string, context):
    f = open(file, 'a')
    f.write(string)
    f.close()

def generate_random_password(size):
    return ''.join(random.choice(string.ascii_uppercase  + string.ascii_lowercase + string.digits) for _ in range(size))

