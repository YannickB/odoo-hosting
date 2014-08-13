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


def log(message, context):
    message = filter(lambda x: x in string.printable, message)
    _logger.info(message)
    log_obj = context['saas-self'].pool.get('saas.log')
    if 'logs' in context:
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


def connect(host, port, username, context):
    log('connect: ssh ' + username + '@' + host + ' -p ' + str(port), context)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=int(port), username=username)
    sftp = ssh.open_sftp()
    return (ssh, sftp)

def execute(ssh, cmd, context, stdin_arg=False):
    log('command : ' + ' '.join(cmd), context)
    stdin, stdout, stderr = ssh.exec_command(' '.join(cmd))
    if stdin_arg:
        for arg in stdin_arg:
            log('command : ' + arg, context)
            stdin.write(arg)
            log('Done', context)
        stdin.flush()
#    _logger.info('stdin : %s', stdin.read())
    stdout_read = stdout.read()
    log('stdout : ' + stdout_read, context)
    log('stderr : ' + stderr.read(), context)
    return stdout_read

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

