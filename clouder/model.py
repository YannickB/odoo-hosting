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


from openerp import models, fields, api, _, tools, release
from openerp.exceptions import except_orm
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import\
    job, whitelist_unpickle_global

from datetime import datetime
import subprocess
import os.path
import string
import copy_reg
import errno
import random
import re
import requests
import time
import select

from os.path import expanduser

import logging
_logger = logging.getLogger(__name__)

try:
    import paramiko
except ImportError:
    _logger.debug('Cannot `import paramiko`.')

ssh_connections = {}


@job
def connector_enqueue(
        session, model_name, record_id, func_name,
        action, job_id, context, *args, **kargs):

    context = context.copy()
    context.update(session.env.context.copy())
    with session.change_context(context):
        record = session.env[model_name].browse(record_id)

    job = record.env['queue.job'].search([
        ('uuid', '=', record.env.context['job_uuid'])])
    clouder_jobs = record.env['clouder.job'].search([('job_id', '=', job.id)])
    clouder_jobs.write({'log': False})
    job.env.cr.commit()

    priority = record.control_priority()
    if priority:
        job.write({'priority': priority + 1})
        job.env.cr.commit()
        raise except_orm(
            _('Priority error!'),
            _("Waiting for another job to finish"))

    res = getattr(record, func_name)(action, job_id, *args, **kargs)
    # if 'clouder_unlink' in record.env.context:
    #     res = super(ClouderModel, record).unlink()
    record.log('===== END JOB ' + session.env.context['job_uuid'] + ' =====')
    job.search([('state', '=', 'failed')]).write({'state': 'pending'})
    return res

# Add function in connector whitelist
whitelist_unpickle_global(copy_reg._reconstructor)
whitelist_unpickle_global(tools.misc.frozendict)
whitelist_unpickle_global(dict)
whitelist_unpickle_global(connector_enqueue)


class ClouderJob(models.Model):
    """
    Define the clouder.job,
    used to store the log and it needed link to the connector job.
    """

    _name = 'clouder.job'

    log = fields.Text('Log')
    name = fields.Char('Description')
    action = fields.Char('Action')
    res_id = fields.Integer('Res ID')
    model_name = fields.Char('Model')
    create_date = fields.Datetime('Created at')
    create_uid = fields.Many2one('res.users', 'By')
    start_date = fields.Datetime('Started at')
    end_date = fields.Datetime('Ended at')
    job_id = fields.Many2one('queue.job', 'Connector Job')
    job_state = fields.Selection([
        ('pending', 'Pending'),
        ('enqueud', 'Enqueued'),
        ('started', 'Started'),
        ('done', 'Done'),
        ('failed', 'Failed')], 'Job State',
        related='job_id.state', readonly=True)
    state = fields.Selection([
        ('started', 'Started'), ('done', 'Done'), ('failed', 'Failed')],
        'State', readonly=True, required=True, select=True)

    _order = 'create_date desc'


class ClouderModel(models.AbstractModel):
    """
    Define the clouder.model abstract object, which is inherited by most
    objects in clouder.
    """

    _name = 'clouder.model'

    _autodeploy = True

    # We create the name field to avoid warning for the constraints
    name = fields.Char('Name', required=True)
    job_ids = fields.One2many(
        'clouder.job', 'res_id',
        domain=lambda self: [('model_name', '=', self._name)],
        auto_join=True, string='Jobs')

    @property
    def version(self):
        return int(release.version.split('.')[0])

    @property
    def email_sysadmin(self):
        """
        Property returning the sysadmin email of the clouder.
        """
        return self.env.ref('clouder.clouder_settings').email_sysadmin

    @property
    def salt_master(self):
        """
        Property returning the salt master of the clouder.
        """
        return self.env.ref('clouder.clouder_settings').salt_master_id

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
    def now(self):
        """
        Property returning the actual date.
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

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

    @api.multi
    @api.constrains('name')
    def _check_config(self):
        """
        Check that we specified the sysadmin email in configuration before
        making any action.
        """
        if self._name != 'clouder.config.settings' and not \
                self.env.ref('clouder.clouder_settings').email_sysadmin:
            raise except_orm(
                _('Data error!'),
                _("You need to specify the sysadmin email in configuration"))

    @api.multi
    def check_priority(self):
        priority = False
        for record_job in self.job_ids:
            if record_job.job_id and record_job.job_id.state != 'done' and \
                    record_job.job_id.priority <= 999:
                priority = record_job.job_id.priority
        return priority

    @api.multi
    def control_priority(self):
        return False

    @api.multi
    def log(self, message):
        """
        Add a message in the logs specified in context.

        :param message: The message which will be logged.
        """
        job_obj = self.env['clouder.job']
        now = datetime.now()
        message = re.sub(r'$$$\w+$$$', '**********', message)
        message = filter(lambda x: x in string.printable, message)
        _logger.info(message)

        if 'clouder_jobs' in self.env.context:
            for key, job_id in self.env.context['clouder_jobs'].iteritems():
                if job_obj.search([('id', '=', job_id)]):
                    job = job_obj.browse(job_id)
                    if job.state == 'started':
                        job.log = (job.log or '') +\
                            now.strftime('%Y-%m-%d %H:%M:%S') + ' : ' +\
                            message + '\n'
        self.env.cr.commit()

    def raise_error(self, message):
        self.log('Raising error :' + message)
        self.log('Version :' + str(self.version))
        if self.version >= 9:
            from openerp.exceptions import UserError
            raise UserError(message)
        else:
            # from openerp.exceptions import except_orm
            raise except_orm(_(''), _(message))

    @api.multi
    def do(self, name, action, where=False):
        where = where or self
        if 'clouder_jobs' not in self.env.context:
            self = self.with_context(clouder_jobs={})
        job_id = False
        key = where._name + '_' + str(where.id)
        if key not in self.env.context['clouder_jobs']:
            job = self.env['clouder.job'].create({
                'name': name, 'action': action, 'model_name': where._name,
                'res_id': where.id, 'state': 'started'})
            jobs = self.env.context['clouder_jobs']
            jobs[key] = job.id
            self = self.with_context(clouder_jobs=jobs)
            job_id = job.id

#        if 'no_enqueue' not in self.env.context:
#            self.enqueue(name, action, job_id)
#        else:
        getattr(self, 'do_exec')(action, job_id)

    @api.multi
    def enqueue(self, name, action, clouder_job_id):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        job_uuid = connector_enqueue.delay(
            session, self._name, self.id, 'do_exec', action, clouder_job_id,
            self.env.context, description=name,
            max_retries=0)
        job_id = self.env['queue.job'].search([('uuid', '=', job_uuid)])[0]
        clouder_job = self.env['clouder.job'].browse(clouder_job_id)
        clouder_job.write({'job_id': job_id.id})

    @api.multi
    def do_exec(self, action, job_id):

        if job_id:
            job = self.env['clouder.job'].browse(job_id)
            job.write({'start_date': self.now})

        try:
            getattr(self, action)()
            if job_id:
                job.write({'end_date': self.now, 'state': 'done'})
        except:
            self.log('===================')
            self.log('FAIL!')
            self.log('===================')
            if job_id:
                job.write({'end_date': self.now, 'state': 'failed'})
            raise

    @api.multi
    def deploy_frame(self):
        try:
            self.deploy()
            self.deploy_links()
        except:
            self.log('===================')
            self.log('FAIL! Reverting...')
            self.log('===================')
            self.purge()
            raise

    @api.multi
    def deploy(self):
        """
        Hook which can be used by inheriting objects to execute actions when
        we create a new record.
        """
        self.purge()
        return

    @api.multi
    def purge(self):
        """
        Hook which can be used by inheriting objects to execute actions when
        we delete a record.
        """
        self.purge_links()
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
        self.do('reinstall', 'deploy_frame')

    @api.multi
    def hook_create(self):
        return

    @api.model
    def create(self, vals):
        """
        Override the default create function to create log, call deploy hook,
        and call unlink if something went wrong.

        :param vals: The values needed to create the record.
        """

        res = super(ClouderModel, self).create(vals)

        if self._autodeploy:
            res.hook_create()
            res.do('create', 'deploy_frame')

        return res

    @api.multi
    def unlink(self):
        """
        Override the default unlink function to create log and call purge hook.
        """
        for rec in self:
            if self._autodeploy:
                try:
                    rec.purge()
                except:
                    pass
        res = super(ClouderModel, self).unlink()
        self.env['clouder.job'].search([
            ('res_id', 'in', self.ids),
            ('model_name', '=', self._name)]).unlink()
        return res

    @api.multi
    def connect(self, server_name='', port=False, username=False):
        """
        Method which can be used to get an ssh connection to execute command.

        :param host: The host we need to connect.
        :param port: The port we need to connect.
        :param username: The username we need to connect.
        """

        server = self
        if self._name == 'clouder.container':
            username = False
            server = self.server_id

        if not server_name:
            server_name = server.fulldomain

        global ssh_connections
        host_fullname = server_name + \
            (port and ('_' + port) or '') + \
            (username and ('_' + username) or '')
        if host_fullname not in ssh_connections\
                or not ssh_connections[host_fullname]._transport:

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh_config = paramiko.SSHConfig()
            user_config_file = os.path.expanduser("~/.ssh/config")
            if os.path.exists(user_config_file):
                with open(user_config_file) as f:
                    ssh_config.parse(f)
            user_config = ssh_config.lookup(server_name)

            identityfile = None
            if 'identityfile' in user_config:
                host = user_config['hostname']
                identityfile = user_config['identityfile']
                if not username:
                    username = user_config['user']
                if not port:
                    port = user_config['port']

            if identityfile is None:
                self.raise_error(
                    "It seems Clouder have no record in the ssh config to "
                    "connect to your server.\nMake sure there is a '" +
                    self.name + ""
                    "' record in the ~/.ssh/config of the Clouder "
                    "system user.\n"
                    "To easily add this record, depending if Clouder try to "
                    "connect to a server or a container, you can click on the"
                    " 'reinstall' button of the server record or 'reset key' "
                    "button of the container record you try to access.")

            # Security with latest version of Paramiko
            # https://github.com/clouder-community/clouder/issues/11
            if isinstance(identityfile, list):
                identityfile = identityfile[0]

            # Probably not useful anymore, to remove later
            if not isinstance(identityfile, basestring):
                raise except_orm(
                    _('Data error!'),
                    _("For unknown reason, it seems the variable identityfile "
                      "in the connect ssh function is invalid. Please report "
                      "this message.\n"
                      "Identityfile : " + str(identityfile) +
                      ", type : " + type(identityfile)))

            self.log('connect: ssh ' + (username and username + '@' or '') +
                     host + (port and ' -p ' + str(port) or ''))

            try:
                ssh.connect(
                    host, port=int(port), username=username,
                    key_filename=os.path.expanduser(identityfile))
            except Exception as inst:
                raise except_orm(
                    _('Connect error!'),
                    _("We were not able to connect to your server. Please "
                      "make sure you add the public key in the "
                      "authorized_keys file of your root user on your server."
                      "\nIf you were trying to connect to a container, "
                      "a click on the 'reset key' button on the container "
                      "record may resolve the problem.\n"
                      "Target : " + host + "\n"
                      "Error : " + str(inst)))
            ssh_connections[host_fullname] = ssh
        else:
            ssh = ssh_connections[host_fullname]

        return {'ssh': ssh, 'host': server_name, 'server': server}

    @api.multi
    def execute(self, cmd, stdin_arg=False,
                path=False, ssh=False, server_name='',
                username=False, executor='bash'):
        """
        Method which can be used with an ssh connection to execute command.

        :param ssh: The connection we need to use.
        :param cmd: The command we need to execute.
        :param stdin_arg: The command we need to execute in stdin.
        :param path: The path where the command need to be executed.
        """

        if self._name == 'clouder.container' \
                and self.childs and 'exec' in self.childs:
            return self.childs['exec'].execute(
                cmd, stdin_arg=stdin_arg, path=path, ssh=ssh,
                server_name=server_name, username=username, executor=executor)

        res_ssh = self.connect(server_name=server_name, username=username)
        ssh, host = res_ssh['ssh'], res_ssh['host']

        if path:
            self.log('path : ' + path)
            cmd.insert(0, 'cd ' + path + ';')

        if self._name == 'clouder.container':
            cmd_temp = []
            first = True
            for cmd_arg in cmd:
                cmd_arg = cmd_arg.replace('"', '\\"')
                if first:
                    cmd_arg = '"' + cmd_arg
                first = False
                cmd_temp.append(cmd_arg)
            cmd = cmd_temp
            cmd.append('"')
            cmd.insert(0, self.name + ' ' + executor + ' -c ')
            if username:
                cmd.insert(0, '-u ' + username)
            cmd.insert(0, 'docker exec')

        self.log('host : ' + host)
        self.log('command : ' + ' '.join(cmd))
        cmd = [c.replace('$$$', '') for c in cmd]

        transport = ssh.get_transport()
        channel = transport.open_session()
        channel.exec_command(' '.join(cmd))

        # Pushing additional input
        if stdin_arg:
            chnl_stdin = channel.makefile('wb', -1)
            for arg in stdin_arg:
                self.log('command : ' + arg)
                chnl_stdin.write(arg)
                chnl_stdin.flush()

        # Reading outputs
        stdout_read = ''
        chnl_out = ''
        chnl_err = ''
        chnl_buffer_size = 4096
        # As long as the command is running
        while not channel.exit_status_ready():
            rl, _, _ = select.select([channel], [], [], 0.0)
            if len(rl) > 0:
                # Polling and printing stdout
                if channel.recv_ready():
                    chnl_out += channel.recv(chnl_buffer_size)
                    stdout_read += chnl_out
                    chnl_pending_out = chnl_out.split('\n')
                    chnl_out = chnl_pending_out[-1]
                    for output_to_print in chnl_pending_out[:-1]:
                        self.log('stdout : {0}'.format(output_to_print))
                # Polling and printing stderr
                if channel.recv_stderr_ready():
                    chnl_err += channel.recv_stderr(chnl_buffer_size)
                    chnl_pending_err = chnl_err.split('\n')
                    chnl_err = chnl_pending_err[-1]
                    for err_to_print in chnl_pending_err[:-1]:
                        self.log('stderr : {0}'.format(err_to_print))

        # Polling last outputs if any:
        rl, _, _ = select.select([channel], [], [], 0.0)
        if len(rl) > 0:
            # Polling and printing stdout
            if channel.recv_ready():
                chnl_out += channel.recv(chnl_buffer_size)
                stdout_read += chnl_out
                chnl_pending_out = chnl_out.split('\n')
                for output_to_print in chnl_pending_out:
                    # The last one MAY be empty
                    if output_to_print:
                        self.log('stdout : {0}'.format(output_to_print))
            # Polling and printing stderr
            if channel.recv_stderr_ready():
                chnl_err += channel.recv_stderr(chnl_buffer_size)
                chnl_pending_err = chnl_err.split('\n')
                for err_to_print in chnl_pending_err:
                    # The last one MAY be empty
                    if err_to_print:
                        self.log('stderr : {0}'.format(err_to_print))
        return stdout_read

    @api.multi
    def get(self, source, destination, ssh=False):
        """
        Method which can be used with an ssh connection to transfer files.

        :param ssh: The connection we need to use.
        :param source: The path we need to get the file.
        :param destination: The path we need to send the file.
        """

        if self._name == 'clouder.container' and self.childs \
                and 'exec' in self.childs:
            return self.childs['exec'].get(source, destination, ssh=ssh)

        host = self.name
        if self._name == 'clouder.container':
            # TODO
            self.insert(0, 'docker exec ' + self.name)
            host = self.server_id.name

        if not ssh:
            ssh = self.connect(host)

        sftp = ssh.open_sftp()
        self.log('get : ' + source + ' to ' + destination)
        sftp.get(source, destination)
        sftp.close()

    @api.multi
    def send(self, source, destination, ssh=False, username=False):
        """
        Method which can be used with an ssh connection to transfer files.

        :param ssh: The connection we need to use.
        :param source: The path we need to get the file.
        :param destination: The path we need to send the file.
        """

        if self._name == 'clouder.container' and self.childs \
                and 'exec' in self.childs:
            return self.childs['exec'].send(
                source, destination, ssh=ssh, username=username)

        res_ssh = self.connect(username=username)
        ssh, server = res_ssh['ssh'], res_ssh['server']

        final_destination = destination
        tmp_dir = False
        if self != server:
            tmp_dir = '/tmp/clouder/' + str(time.time())
            server.execute(['mkdir', '-p', tmp_dir])
            destination = tmp_dir + '/file'

        sftp = ssh.open_sftp()
        self.log('send : ' + source + ' to ' + destination)
        sftp.put(source, destination)
        sftp.close()

        if tmp_dir:
            server.execute([
                'cat', destination, '|', 'docker', 'exec', '-i',
                username and ('-u ' + username) or '',
                self.name, 'sh', '-c', "'cat > " + final_destination + "'"])
#            if username:
#                server.execute([
#                    'docker', 'exec', '-i', self.name,
#                    'chown', username, final_destination])
            server.execute(['rm', '-rf', tmp_dir])

    @api.multi
    def send_dir(self, source, destination, ssh=False, username=False):
        self.log('Send directory ' + source + ' to ' + destination)
        self.execute(['mkdir', '-p', destination])
        for dirpath, dirnames, filenames in os.walk(source):
            self.log('dirpath ' + str(dirpath))
            self.log('dirnames ' + str(dirnames))
            self.log('filenames ' + str(filenames))
            relpath = os.path.relpath(dirpath, source)
            for dirname in dirnames:
                remote_path = os.path.join(
                    destination, os.path.join(relpath, dirname))
                self.execute(['mkdir', '-p', remote_path])
            for filename in filenames:
                local_path = os.path.join(dirpath, filename)
                remote_filepath = os.path.join(
                    destination, os.path.join(relpath, filename))
                self.send(
                    local_path, remote_filepath, ssh=ssh, username=username)

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
        for line in iter(proc.stdout.readline, b''):
            out += line
            self.log("stdout : {0}".format(line))

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
    def execute_write_file(self, localfile, value, operator='a'):
        """
        Method which write in a file on the local system.

        :param localfile: The path to the file we need to write.
        :param value: The value we need to write in the file.
        """
        f = open(localfile, operator)
        f.write(value)
        f.close()

    def request(
            self, url, method='get', headers=None,
            data=None, params=None, files=None):

        if not headers:
            headers = {}
        if not data:
            data = {}
        if not params:
            params = {}
        if not files:
            files = {}

        self.log('request ' + method + ' ' + url)
        if headers:
            self.log('headers ' + str(headers))
        if data:
            self.log('data ' + str(data))
        if params:
            self.log('params ' + str(params))
        if files:
            self.log('files ' + str(files))
        result = requests.request(
            method, url, headers=headers, data=data,
            params=params, files=files, verify=False)
        self.log('status ' + str(result.status_code) + ' ' + result.reason)
        self.log('result ' + str(result.json()))
        return result


class ClouderTemplateOne2many(models.AbstractModel):

    _name = 'clouder.template.one2many'

    @api.multi
    def reset_template(self, records=None):

        if not records:
            records = []

        if self.template_id:
            if not records:
                records = self.env[self._template_parent_model].search(
                    [('template_ids', 'in', self.template_id.id)])
            for record in records:
                name = hasattr(self.name, 'id') and self.name.id or self.name
                childs = self.search([
                    (self._template_parent_many2one, '=', record.id),
                    ('name', '=', name)])
                vals = {}
                for field in self._template_fields:
                    vals[field] = getattr(self, field)
                if childs:
                    for child in childs:
                        child.write(vals)
                else:
                    vals.update({
                        self._template_parent_many2one: record.id,
                        'name': name})
                    self.create(vals)

    @api.model
    def create(self, vals):
        """
        """
        res = super(ClouderTemplateOne2many, self).create(vals)
        self.reset_template()
        return res

    @api.multi
    def write(self, vals):
        """
        """
        res = super(ClouderTemplateOne2many, self).write(vals)
        self.reset_template()
        return res


def generate_random_password(size):
    """
    Method which can be used to generate a random password.

    :param size: The size of the random string we need to generate.
    """
    return ''.join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase +
                      string.digits)
        for _ in range(size))
