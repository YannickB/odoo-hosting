# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

import errno
import logging
import os.path
import re
import requests
import select
import string
import subprocess
import sys
import time
import traceback

from contextlib import contextmanager
from datetime import datetime
from os.path import expanduser

try:
    from odoo import models, fields, api, _, release
except ImportError:
    from openerp import models, fields, api, _, release

from ..exceptions import ClouderError
from ..ssh.environment import SSHEnvironment


_logger = logging.getLogger(__name__)

try:
    import paramiko
except ImportError:
    _logger.warning('Cannot `import paramiko`.')


class ClouderModel(models.AbstractModel):
    """
    Define the clouder.model abstract object, which is inherited by most
    objects in clouder.
    """

    _name = 'clouder.model'
    _description = 'Clouder Model'

    _autodeploy = True

    BACKUP_BASE_DIR = '/base-backup/'
    BACKUP_DATA_DIR = '/opt/backup/'
    BACKUP_HOME_DIR = '/home/backup/'
    BACKUP_DATE_FILE = 'backup-date'

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
    def master_id(self):
        """
        Property returning the deployer of the clouder.
        """
        return self.env.ref('clouder.clouder_settings').master_id

    @property
    def runner(self):
        """
        Property returning the runner of the clouder.
        """
        return self.env.ref('clouder.clouder_settings').runner

    @property
    def executor(self):
        """
        Property returning the executor of the clouder.
        """
        return self.env.ref('clouder.clouder_settings').executor

    @property
    def compose(self):
        """
        Property returning the compose of the clouder.
        """
        return self.env.ref('clouder.clouder_settings').compose

    @property
    def salt_master(self):
        """
        Property returning the salt master of the clouder.
        """
        return self.env.ref('clouder.clouder_settings').salt_master_id

    @property
    def user_partner(self):
        """
        Property returning the full name of the node.
        """
        return self.env['res.partner'].search(
            [('user_ids', 'in', int(self.env.uid))])[0]

    @property
    def archive_path(self):
        """
        Property returning the path where are stored the archives
        in the archive service.
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
    def get_directory_key(self, add_path=None):
        """ It returns the current working directory for keys
        :param add_path: (str|iter) String or Iterator of Strings indicating
            path parts to add to the default remote working path
        :returns: (str) Key directory on the local
        """
        name = 'key_%s' % self.env.uid
        return self._get_directory_tmp(name, add_path)

    @api.multi
    def get_directory_clouder(self, add_path=None):
        """ It returns the current clouder directory on the remote
        :param add_path: (str|iter) String or Iterator of Strings indicating
            path parts to add to the default remote working path
        :returns: (str) Clouder directory on the remote
        """
        return self._get_directory_tmp('clouder', add_path)

    @api.multi
    def _get_directory_tmp(self, name, add_path=None):
        """ It returns a directory in tmp for name
        :param name: (str) Name of the directory in tmp
        :param add_path: (str|iter) String or Iterator of Strings indicating
            path parts to add to the default remote working path
        :returns: (str) Clouder directory on the remote
        """
        if add_path is None:
            add_path = []
        elif not isinstance(add_path, (tuple, list, dict)):
            add_path = [str(add_path)]
        return os.path.join('/tmp', str(name), *add_path)

    @api.multi
    @contextmanager
    def _private_env(self):
        """ It provides an isolated environment/commit

        Usage:
            ``with self._private_env() as self``

        Yields:
            Current ``self``, but in a new environment
        """
        # with api.Environment.manage():
        #     with registry(self.env.cr.dbname).cursor() as cr:
        #         env = api.Environment(cr, self.env.uid, self.env.context)
        #         _logger.debug('Created new env %s for %s', env, self)
        yield self
        self.env.cr.commit()  # pylint: disable=E8102
        #         _logger.debug('Cursor %s has been committed', cr)

    @api.multi
    @api.constrains('name')
    def _check_config(self):
        """
        Check that we specified the sysadmin email in configuration before
        making any action.
        """
        if self._name != 'clouder.config.settings' and not \
                self.env.ref('clouder.clouder_settings').email_sysadmin:
            self.raise_error(
                "You need to specify the sysadmin email in configuration.",
            )

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

        with self._private_env() as self:

            job_obj = self.env['clouder.job']
            now = fields.Datetime.now()
            message = re.sub(r'$$$\w+$$$', '**********', message)
            message = filter(lambda x: x in string.printable, message)
            _logger.info(message)

            if 'clouder_jobs' not in self.env.context:
                return

            for key, job_id in self.env.context['clouder_jobs'].iteritems():
                if job_obj.search([('id', '=', job_id)]):
                    job = job_obj.browse(job_id)
                    if job.state == 'started':
                        job.log = '%s%s : %s\n' % (
                            (job.log or ''),
                            now,
                            message,
                        )

    @api.multi
    def log_error(self, trace=True, reverting=False):
        """ It logs a unified fail message with posibility of tracebacks
        :param trace: (bool) Include a traceback in the log
        :param reverting: (bool) Include a message about reverting in the log
        """
        self.log('===================')
        self.log('FAIL!%s' % (' Reverting...' if reverting else ''))
        if trace:
            ex_type, ex, tb = sys.exc_info()
            if ex_type is not None:
                tb = '\n'.join(traceback.format_tb(tb))
                self.log(tb)
        self.log('===================')

    @api.multi
    def raise_error(self, message, interpolations=None):
        """ Raises a ClouderError with a translated message
        :param message: (str) Message including placeholders for string
            interpolation. Interpolation takes place via the ``%`` operator.
        :param interpolations: (dict|tuple) Mixed objects to be used for
            string interpolation after message translation. Dict for named
            parameters or tuple for positional. Cannot use both.
        :raises: (clouder.exceptions.ClouderError)
        """
        if interpolations is None:
            interpolations = ()
        elif isinstance(interpolations, basestring):
            interpolations = (interpolations, )
        raise ClouderError(self, _(message) % interpolations)

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
        return

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
            self.log_error()
            if job_id:
                job.write({'end_date': self.now, 'state': 'failed'})
            raise

    @api.multi
    def deploy_frame(self):
        self.ensure_one()
        try:
            self.deploy()
        except:
            self.log_error(reverting=True)
            self.purge()
            raise

    @api.multi
    def deploy(self):
        """
        Hook which can be used by inheriting objects to execute actions when
        we create a new record.
        """
        self.ensure_one()
        self.purge()
        return

    @api.multi
    def purge(self):
        """
        Hook which can be used by inheriting objects to execute actions when
        we delete a record.
        """
        self.ensure_one()
        self.purge_links()
        return

    @api.multi
    def deploy_links(self):
        """
        Force deployment of all links linked to a record.
        """
        self.ensure_one()
        if hasattr(self, 'link_ids'):
            for link in self.link_ids:
                if link.auto:
                    link.deploy_()

    @api.multi
    def purge_links(self):
        """
        Force purge of all links linked to a record.
        """
        self.ensure_one()
        if hasattr(self, 'link_ids'):
            for link in self.link_ids:
                if link.auto:
                    link.purge_()

    @api.multi
    def reinstall(self):
        """"
        Action which purge then redeploy a record.
        """
        self.ensure_one()
        self.do('reinstall', 'deploy_frame')

    @api.multi
    def hook_create(self, vals):
        self.ensure_one()
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
            res.hook_create(vals)
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
    def connect(self, host=None, username=None, port=None):
        """ It provides an SSHEnvironment for use

        Params:
            host: (str|None) IP/Host name of remote node. None to compile from
                recordset
            username: (str|None) Username to login to remote node. None for
                blank.
            port: (int|None) SSH port of remote node. None for default (22)

        Returns:
            clouder.ssh.SSHEnvironment: SSH Environment representing remote
                node

        Raises:
            clouder.exceptions.ClouderError: If the connection failed or was
                terminated unexpectedly
        """

        self.ensure_one()

        node = self
        if self._name == 'clouder.service':
            username = False
            node = self.node_id

        if not host:
            host = node.fulldomain

        self.log('connect: ssh %s%s%s' % (
            username and '%s@' % username or '',
            host,
            port and ' -p %s' % port or '',
        ))

        identity_file, host, username, port = self.__identity_file(
            host, username, port
        )

        try:
            env = SSHEnvironment(
                host, port, username, identity_file,
            )
        except Exception as e:
            self.raise_error(
                'We were not able to connect to your node. Please '
                'make sure you add the public key in the '
                'authorized_keys file of your root user on your node.\n'
                'If you were trying to connect to a service, '
                'a click on the "Reset Key" button on the service '
                'record may resolve the problem.\n\n'
                'Target: "%s" \n'
                'Error: \n%r',
                (host, e),
            )

        env.node_record = node
        return env

    @api.multi
    def __identity_file(self, node_name, username, port):
        """ It processes the Identity File for use with remote node

        Returns:
            tuple(identity_file, host, username, port)
        """

        ssh_config = paramiko.SSHConfig()
        user_config_file = os.path.expanduser("~/.ssh/config")
        if os.path.exists(user_config_file):
            with open(user_config_file) as f:
                ssh_config.parse(f)
        user_config = ssh_config.lookup(node_name)

        identity_file = None
        if 'identityfile' in user_config:
            host = user_config['hostname']
            identity_file = user_config['identityfile']
            if not username:
                username = user_config['user']
            if not port:
                port = user_config['port']

        if identity_file is None:
            self.raise_error(
                'Clouder does not have a record in the ssh config to '
                'connect to your node.\n'
                'Make sure there is a "%s" record in the "~/.ssh/config" '
                'of the Clouder system user.\n'
                'To easily add this record, you can click on the '
                '"Reinstall" button of the node record, or the '
                '"Reset Key" button of the service record you are '
                'trying to access',
                self._name,
            )

        # Security with latest version of Paramiko
        # https://github.com/clouder-community/clouder/issues/11
        if isinstance(identity_file, list):
            identity_file = identity_file[0]

        # Probably not useful anymore, to remove later
        if not isinstance(identity_file, basestring):
            self.raise_error(
                'For an unknown reason, the variable identityfile '
                'in the connect ssh function is invalid. Please report '
                'this message.\n'
                'IdentityFile: "%s", Type: "%s"',
                (identity_file, type(identity_file)),
            )

        return identity_file, host, username, int(port)

    @api.multi
    def execute(self, cmd, stdin_arg=None,
                path=None, ssh=None, node_name=None,
                username=False, shell='bash',
                ):
        """ It (possibly) connects and executes a command on a remote node

        Params:
            cmd: (iter) Iterator of string commands to execute on node
            stdin_arg: (iter|None) Iterator of string commands to execute in
                ``stdin``.
            path: (str|None) Working directory on remote node for cmd
                execution. None will execute in current channel working
                directory, which is usually ``$HOME``.
            ssh: (clouder.ssh.environment.SSHEnvironment) Will use this
                instead of connecting to a new session, if provided
            node_name: (str|None) Name of node to connect to. None to
                use the default for the Recordset. Will be ignored if a
                ``session`` dict is provided.
            username: (str|None) Name of user on remote node. None to
                use the default for the Recordset.
            shell: (str) Name (or path) of shell binary to use for execution
        """

        if not ssh:
            ssh = self.connect(node_name, username=username)
        for record in self:
            res = record.__execute(cmd, stdin_arg, path, ssh, username, shell)
        return res

    @api.multi
    def __execute(self, cmd, stdin_arg, path, ssh, username, shell):
        """ It executes a command on a pre-existing SSH channel """

        self.ensure_one()

        if all([self._name == 'clouder.service',
                'exec' in getattr(self, 'childs', []),
                ]):
                return self.childs['exec'].execute(
                    cmd, stdin_arg=stdin_arg, path=path, ssh=ssh,
                    username=username, shell=shell,
                )

        if path:
            self.log('path : ' + path)
            cmd.insert(0, 'cd ' + path + ';')

        if self._name == 'clouder.service':

            service = self.pod

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

            cmd.insert(0, '%s %s -c ' % (service, shell))

            if username:
                cmd.insert(0, '-u ' + username)
            cmd.insert(0, 'docker exec')

        self.log('')
        self.log('host : ' + ssh.host)
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
    def get(self, source, destination, ssh=None):
        """
        Method which can be used with an ssh connection to transfer files.

        :param ssh: The connection we need to use.
        :param source: The path we need to get the file.
        :param destination: The path we need to send the file.
        """

        for record in self:

            if all([record._name == 'clouder.service',
                    'exec' in getattr(record, 'childs', []),
                    ]):
                return record.childs['exec'].get(
                    source, destination, ssh=ssh,
                )

            host = record.name
            if record._name == 'clouder.service':
                # TODO
                record.insert(0, 'docker exec ' + record.name)
                host = record.node_id.name

            if not ssh:
                ssh = record.connect(host)

            sftp = ssh.open_sftp()
            record.log('get: "%s" => "%s"' % (source, destination))
            sftp.get(source, destination)
            sftp.close()

    @api.multi
    def send(self, source, destination, ssh=None, username=None):
        """
        Method which can be used with an ssh connection to transfer files.

        :param ssh: The connection we need to use.
        :param source: The path we need to get the file.
        :param destination: The path we need to send the file.
        """

        for record in self:
            if all([record._name == 'clouder.service',
                    'exec' in getattr(record, 'childs', []),
                    ]):
                return record.childs['exec'].send(
                    source, destination, ssh=ssh, username=username,
                )

            if not ssh:
                ssh = record.connect(username=username)

            final_destination = destination
            tmp_dir = False
            if record != ssh.node_record:
                tmp_dir = record.get_directory_clouder(time.time())
                ssh.node_record.execute(['mkdir', '-p', tmp_dir])
                destination = os.path.join(tmp_dir, 'file')

            sftp = ssh.open_sftp()
            record.log('send: "%s" to "%s"' % (source, destination))
            sftp.put(source, destination)
            sftp.close()

            if tmp_dir:
                ssh.node_record.execute([
                    'cat', destination, '|', 'docker', 'exec', '-i',
                    username and ('-u %s' % username) or '',
                    record.pod, 'sh', '-c',
                    "'cat > %s'" % final_destination,
                ])
    #            if username:
    #                ssh.node_record.execute([
    #                    'docker', 'exec', '-i', self.name,
    #                    'chown', username, final_destination])
                ssh.node_record.execute(['rm', '-rf', tmp_dir])

    @api.multi
    def send_dir(self, source, destination, ssh=False, username=False):
        self.ensure_one()
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
        except IOError as e:
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
        with open(localfile, operator) as f:
            f.write(value)

    def request(
            self, url, method='get', headers=None,
            data=None, params=None, files=None):

        self.log('request "%s" "%s"' % (method, url))

        if headers is None:
            headers = {}
        else:
            self.log('request "%s" "%s"' % (method, url))

        if data is None:
            data = {}
        else:
            self.log('data %s' % data)

        if params is None:
            params = {}
        else:
            self.log('params %s' % params)

        if files is None:
            files = {}
        else:
            self.log('files %s' % files)

        result = requests.request(
            method, url, headers=headers, data=data,
            params=params, files=files, verify=False,
        )
        self.log('status %s %s' % (result.status_code, result.reason))
        self.log('result %s' % result.json())

        return result
