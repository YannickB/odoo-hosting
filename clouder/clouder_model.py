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


from openerp import models, fields, api, _
from openerp.exceptions import except_orm

from datetime import datetime, timedelta
import subprocess
import paramiko
import os.path
import string
import errno
import random

from os.path import expanduser

import logging
_logger = logging.getLogger(__name__)

ssh_connections = {}

class ClouderLog(models.Model):
    """
    Define the log object, where is stored the log of the commands after
    we execute an action.
    """

    _name = 'clouder.log'

    @api.one
    def _get_name(self):
        """
        Return the name of the record linked to this log.
        """
        model_obj = self.env[self.model]
        record = model_obj.browse(self.res_id)
        if record and hasattr(record, 'name'):
            self.name = record.name
        return

    model = fields.Char('Related Document Model', size=128, select=1)
    res_id = fields.Integer('Related Document ID', select=1)
    name = fields.Char('Name', compute='_get_name', size=128)
    action = fields.Char('Action', size=64)
    description = fields.Text('Description')
    state = fields.Selection(
        [('unfinished', 'Not finished'), ('ok', 'Ok'), ('ko', 'Ko')],
        'State', required=True, default='unfinished')
    create_date = fields.Datetime('Launch Date')
    finish_date = fields.Datetime('Finish Date')
    expiration_date = fields.Datetime('Expiration Date')

    _order = 'create_date desc'


class ClouderModel(models.AbstractModel):
    """
    Define the clouder.model abstract object, which is inherited by most
    objects in clouder.
    """

    _name = 'clouder.model'

    _log_expiration_days = 30
    _autodeploy = True

    # We create the name field to avoid warning for the constraints
    name = fields.Char('Name', size=64, required=True)
    log_ids = fields.One2many(
        'clouder.log', 'res_id',
        domain=lambda self: [('model', '=', self._name)],
        auto_join=True, string='Logs')

    @property
    def email_sysadmin(self):
        """
        Property returning the sysadmin email of the clouder.
        """
        return self.env.ref('clouder.clouder_settings').email_sysadmin

    @property
    def user_partner(self):
        """
        Property returning the full name of the server.
        """
        return self.env['res.partner'].search(
            [('user_ids', 'in', int(self.env.uid))])[0]

    @property
    def archive_path(self):
        """
        Property returning the path where are stored the archives
        in the archive container.
        """
        return '/opt/archives'

    @property
    def services_hostpath(self):
        """
        Property returning the path where are stored the archives
        in the host system.
        """
        return '/opt/services'

    @property
    def home_directory(self):
        """
        Property returning the path to the home directory.
        """
        return expanduser("~")

    @property
    def now_date(self):
        """
        Property returning the actual date.
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d")

    @property
    def now_hour(self):
        """
        Property returning the actual hour.
        """
        now = datetime.now()
        return now.strftime("%H-%M")

    @property
    def now_hour_regular(self):
        """
        Property returning the actual hour.
        """
        now = datetime.now()
        return now.strftime("%H:%M:%S")

    @property
    def now_bup(self):
        """
        Property returning the actual date, at the bup format.
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d-%H%M%S")

    @api.one
    @api.constrains('name')
    def _check_config(self):
        """
        Check that we specified the sysadmin email in configuration before
        making any action.
        """
        if not self.env.ref('clouder.clouder_settings').email_sysadmin:
            raise except_orm(
                _('Data error!'),
                _("You need to specify the sysadmin email in configuration"))

    @api.multi
    def create_log(self, action):
        """
        Create the log record and add his id in context.

        :param action: The action which trigger the log.
        """
        if 'log_id' in self.env.context:
            return self.env.context

        if 'logs' in self.env.context:
            logs = self.env.context['logs']
        else:
            logs = {}

        if not self._name in logs:
            logs[self._name] = {}
        now = datetime.now()
        if not self.id in logs[self._name]:
            expiration_date = (
                now + timedelta(days=self._log_expiration_days)
            ).strftime("%Y-%m-%d")
            log_id = self.env['clouder.log'].create({
                'model': self._name, 'res_id': self.id,
                'action': action, 'expiration_date': expiration_date})
            logs[self._name][self.id] = {}
            logs[self._name][self.id]['log_model'] = self._name
            logs[self._name][self.id]['log_res_id'] = self.id
            logs[self._name][self.id]['log_id'] = log_id.id
            logs[self._name][self.id]['log_log'] = ''

        self = self.with_context(logs=logs)
        return self.env.context

    @api.multi
    def end_log(self):
        """
        Close the log record if the action finished correctly.
        """
        log_obj = self.env['clouder.log']
        if 'logs' in self.env.context:
            log = log_obj.browse(
                self.env.context['logs'][self._name][self.id]['log_id'])
            if log.state == 'unfinished':
                log.state = 'ok'

    @api.multi
    def log(self, message):
        """
        Add a message in the logs specified in context.

        :param message: The message which will be logged.
        """
        message = filter(lambda x: x in string.printable, message)
        _logger.info(message)
        log_obj = self.env['clouder.log']
        if 'logs' in self.env.context:
            for model, model_vals in self.env.context['logs'].iteritems():
                for res_id, vals in \
                        self.env.context['logs'][model].iteritems():
                    log = log_obj.browse(
                        self.env.context['logs'][model][res_id]['log_id'])
                    log.description = (log.description or '') + message + '\n'

    @api.multi
    def ko_log(self):
        """
        Ko the log specified in context.
        """
        log_obj = self.env['clouder.log']
        if 'logs' in self.env.context:
            for model, model_vals in self.env.context['logs'].iteritems():
                for res_id, vals in \
                        self.env.context['logs'][model].iteritems():
                    log = log_obj.browse(
                        self.env.context['logs'][model][res_id]['log_id'])
                    log.state = 'ko'

    @api.multi
    def deploy(self):
        """
        Hook which can be used by inheriting objects to execute actions when
        we create a new record.
        """
        return

    @api.multi
    def purge(self):
        """
        Hook which can be used by inheriting objects to execute actions when
        we delete a record.
        """
        return

    @api.multi
    def deploy_links(self):
        """
        Force deployment of all links linked to a record.
        """
        if hasattr(self, 'link_ids'):
            for link in self.link_ids:
                link.deploy_()

    @api.multi
    def purge_links(self):
        """
        Force purge of all links linked to a record.
        """
        if hasattr(self, 'link_ids'):
            for link in self.link_ids:
                link.purge_()

    @api.multi
    def reinstall(self):
        """"
        Action which purge then redeploy a record.
        """
        self = self.with_context(self.create_log('reinstall'))
        self.purge_links()
        self.purge()
        self.deploy()
        self.deploy_links()
        self.end_log()

    @api.model
    def create(self, vals):
        """
        Override the default create function to create log, call deploy hook,
        and call unlink if something went wrong.

        :param vals: The values needed to create the record.
        """
        res = super(ClouderModel, self).create(vals)
        res = res.with_context(res.create_log('create'))
        try:
            res.deploy()
            res.deploy_links()
        except:
            res.log('===================')
            res.log('FAIL! Reverting...')
            res.log('===================')
            res = res.with_context(nosave=True)
            res.unlink()
            raise
        res.end_log()
        return res

    @api.one
    def unlink(self):
        """
        Override the default unlink function to create log and call purge hook.
        """
        try:
            self.purge_links()
            self.purge()
        except:
            pass
        res = super(ClouderModel, self).unlink()
        # Security to prevent log to write in a removed clouder.log
        if 'logs' in self.env.context \
                and self._name in self.env.context['logs'] \
                and self.id in self.env.context['logs'][self._name]:
            del self.env.context['logs'][self._name][self.id]
        log_ids = self.env['clouder.log'].search(
            [('model', '=', self._name), ('res_id', '=', self.id)])
        log_ids.unlink()
        return res

    @api.multi
    def connect(self, host, port=False, username=False):
        """
        Method which can be used to get an ssh connection to execute command.

        :param host: The host we need to connect.
        :param port: The port we need to connect.
        :param username: The username we need to connect.
        """

        # if not 'ssh_connections' in globals():
        #     ssh_connections = {}
        #     global ssh_connections
        global ssh_connections
        host_fullname = host + \
                        (port and ('_' + port) or '') + \
                        (username and ('_' + username) or '')
        if host_fullname not in ssh_connections\
                or not ssh_connections[host_fullname]._transport:

            self.log('connect: ssh ' + (username and username + '@' or '') +
                     host + (port and ' -p ' + str(port) or ''))
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

            if identityfile is None:
                raise except_orm(
                    _('Data error!'),
                    _("It seems Clouder have no record in the ssh config to "
                      "connect to your server.\nMake sure there is a '" + host + ""
                      "' record in the ~/.ssh/config of the Clouder system user.\n"
                      "To easily add this record, depending if Clouder try to "
                      "connect to a server or a container, you can click on the "
                      "'reinstall' button of the server record or 'reset key' "
                      "button of the container record you try to access."))

            # Security with latest version of Paramiko
            # https://github.com/clouder-community/clouder/issues/11
            if isinstance(identityfile, list):
                identityfile = identityfile[0]

            # Probably not useful anymore, to remove later
            if not isinstance(identityfile, basestring):
                raise except_orm(
                    _('Data error!'),
                    _("For unknown reason, it seems the variable identityfile in "
                      "the connect ssh function is invalid. Please report "
                      "this message.\n"
                      "Identityfile : " + str(identityfile)
                      + ", type : " + type(identityfile)))

            try:
                ssh.connect(host, port=int(port), username=username,
                        key_filename=os.path.expanduser(identityfile))
            except Exception as inst:
                raise except_orm(
                    _('Connect error!'),
                    _("We were not able to connect to your server. Please make "
                      "sure you add the public key in the authorized_keys file "
                      "of your root user on your server.\n"
                      "If you were trying to connect to a container, a click on "
                      "the 'reset key' button on the container record may resolve "
                      "the problem.\n"
                      "Target : " + host + "\n"
                      "Error : " + str(inst)))
            ssh_connections[host_fullname] = ssh
        else:
            ssh = ssh_connections[host_fullname]

        return ssh

    @api.multi
    def execute(self, cmd, stdin_arg=False, path=False, ssh=False):
        """
        Method which can be used with an ssh connection to execute command.

        :param ssh: The connection we need to use.
        :param cmd: The command we need to execute.
        :param stdin_arg: The command we need to execute in stdin.
        :param path: The path where the command need to be executed.
        """

        host = self.name
        if path:
            self.log('path : ' + path)
            cmd.insert(0, 'cd ' + path + ';')
        if self._name == 'clouder.container':
            cmd.insert(0, 'docker exec ' + self.name)
            host = self.server_id.name

        if not ssh:
            ssh = self.connect(host)

        self.log('host : ' + host)
        self.log('command : ' + ' '.join(cmd))
        stdin, stdout, stderr = ssh.exec_command(' '.join(cmd))
        if stdin_arg:
            for arg in stdin_arg:
                self.log('command : ' + arg)
                stdin.write(arg)
                stdin.flush()
        stdout_read = stdout.read()
        self.log('stdout : ' + stdout_read)
        self.log('stderr : ' + stderr.read())
        return stdout_read

    @api.multi
    def get(self, source, destination, ssh=False):
        """
        Method which can be used with an ssh connection to transfer files.

        :param ssh: The connection we need to use.
        :param source: The path we need to get the file.
        :param destination: The path we need to send the file.
        """

        host = self.name
        if self._name == 'clouder.container':
            #TODO
            self.insert(0, 'docker exec ' + self.name)
            host = self.server_id.name

        if not ssh:
            ssh = self.connect(host)

        sftp = ssh.open_sftp()
        self.log('get : ' + source + ' to ' + destination)
        sftp.get(source, destination)
        sftp.close()

    @api.multi
    def send(self, source, destination, ssh=False):
        """
        Method which can be used with an ssh connection to transfer files.

        :param ssh: The connection we need to use.
        :param source: The path we need to get the file.
        :param destination: The path we need to send the file.
        """

        host = self.name
        if self._name == 'clouder.container':
            #TODO
            self.insert(0, 'docker exec ' + self.name)
            host = self.server_id.name

        if not ssh:
            ssh = self.connect(host)

        sftp = ssh.open_sftp()
        self.log('send : ' + source + ' to ' + destination)
        sftp.put(source, destination)
        sftp.close()

    @api.multi
    def execute_local(self, cmd, path=False, shell=False):
        """
        Method which can be used to execute command on the local system.

        :param cmd: The command we need to execute.
        :param path: The path where the command shall be executed.
        :param shell: Specify if the command shall be executed in shell mode.
        """
        self.log('command : ' + ' '.join(cmd))
        cwd = os.getcwd()
        if path:
            self.log('path : ' + path)
            os.chdir(path)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, shell=shell)
        out = ''
        for line in proc.stdout:
            out += line
            line = 'stdout : ' + line
            self.log(line)
        os.chdir(cwd)
        return out

    @api.multi
    def exist(self, ssh, path):
        """
        Method which use an ssh connection to check is a file exist.

        :param ssh: The connection we need to use.
        :param path: The path we need to check.
        """
        sftp = ssh.open_sftp()
        try:
            sftp.stat(path)
        except IOError, e:
            if e.errno == errno.ENOENT:
                sftp.close()
                return False
            raise
        else:
            sftp.close()
            return True

    @api.multi
    def local_file_exist(self, localfile):
        """
        Method which check is a file exist on the local system.

        :param localfile: The path to the file we need to check.
        """
        return os.path.isfile(localfile)

    @api.multi
    def local_dir_exist(self, localdir):
        """
        Method which check is a directory exist on the local system.

        :param localdir: The path to the dir we need to check.
        """
        return os.path.isdir(localdir)

    @api.multi
    def execute_write_file(self, localfile, value):
        """
        Method which write in a file on the local system.

        :param localfile: The path to the file we need to write.
        :param value: The value we need to write in the file.
        """
        f = open(localfile, 'a')
        f.write(value)
        f.close()


def generate_random_password(size):
    """
    Method which can be used to generate a random password.

    :param size: The size of the random string we need to generate.
    """
    return ''.join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase
                      + string.digits)
        for _ in range(size))

