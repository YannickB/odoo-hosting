# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from openerp import models, fields, api
from openerp import modules

import os.path
import socket
import re


import logging
_logger = logging.getLogger(__name__)


class ClouderServer(models.Model):
    """
    Define the server object, which represent the servers
    clouder can connect to.
    """

    _name = 'clouder.server'
    _inherit = ['clouder.model']
    _sql_constraints = [
        ('domain_id_name_uniq', 'unique(domain_id, name)',
         'This name already exists on this domain.'),
        ('ip_ssh_port_uniq', 'unique(ip, ssh_port)',
         'Another server is already setup for this SSH Address and Port.'),
    ]

    @api.model
    def _default_private_key(self):
        """
        Generate a couple of keys visible use on the server form, which
        we can easily add to the server to connect it.
        """

        destroy = True
        if not self.local_dir_exist(self.get_directory_key()):
            self._create_key()
            destroy = False

        key = self.execute_local([
            'cat', self.get_directory_key('key'),
        ])

        if destroy:
            self._destroy_key()
        return key

    @api.model
    def _default_public_key(self):
        """
        Generate a couple of keys visible use on the server form, which
        we can easily add to the server to connect it.
        """

        destroy = True
        if not self.local_dir_exist(self.get_directory_key()):
            self._create_key()
            destroy = False

        key = self.execute_local([
            'cat', self.get_directory_key('key.pub'),
        ])

        if destroy:
            self._destroy_key()
        return key

    key_file = fields.Char(
        compute='_compute_key_file',
        store=True,
    )
    name = fields.Char('Prefix', required=True)
    domain_id = fields.Many2one('clouder.domain', 'Domain', required=True)
    ip = fields.Char('IP')
    environment_id = fields.Many2one('clouder.environment', 'Environment',
                                     required=True)
    login = fields.Char('Login')
    ssh_port = fields.Integer('SSH port', default='22')
    manager = fields.Boolean('Manager')
    provider_id = fields.Many2one('clouder.provider', 'Provider')

    private_key = fields.Text(
        'SSH Private Key',
        default=lambda s: s._default_private_key(),
        compute='_compute_private_key',
        inverse='_inverse_private_key',
    )
    public_key = fields.Text(
        'SSH Public Key',
        default=lambda s: s._default_public_key(),
        compute='_compute_public_key',
        inverse='_inverse_public_key',
    )
    start_port = fields.Integer('Start Port', required=True)
    end_port = fields.Integer('End Port', required=True)
    public_ip = fields.Boolean(
        'Assign ports with public ip?',
        help="This is especially useful if you want to have several "
             "infrastructures on the same server, by using same ports but "
             "different ips. Otherwise the ports will be bind to "
             "all interfaces.")
    public = fields.Boolean('Public?')
    supervision_id = fields.Many2one('clouder.container', 'Supervision Server')
    runner_id = fields.Many2one('clouder.container', 'Runner')
    salt_minion_id = fields.Many2one(
        'clouder.container', 'Salt Minion', readonly=True)
    control_dns = fields.Boolean('Control DNS?')
    oneclick_ids = fields.Many2many(
        'clouder.oneclick', 'clouder_server_oneclick_rel',
        'container_id', 'oneclick_id', 'Oneclick Deployment')
    oneclick_ports = fields.Boolean('Assign critical ports?')

    @api.multi
    @api.depends('name', 'domain_id.name')
    def _compute_key_file(self):
        for server in self:
            server.key_file = os.path.join(
                server.home_directory, '.ssh', 'keys',
                '%s.%s' % (server.name, server.domain_id.name),
            )

    @api.multi
    def _create_key(self):
        """
        Generate a key on the filesystem.
        """
        if not self.env.ref('clouder.clouder_settings').email_sysadmin:
            self.raise_error(
                "You need to specify the sysadmin email in configuration",
            )

        self.execute_local(['mkdir', self.get_directory_key()])
        self.execute_local([
            'ssh-keygen', '-t', 'rsa', '-C', self.email_sysadmin, '-f',
            self.get_directory_key('key'), '-N', '',
        ])
        return True

    @api.multi
    def _destroy_key(self):
        """
        Destroy the key after once we don't need it anymore.
        """
        self.execute_local(['rm', '-rf', self.get_directory_key()])
        return True

    @api.multi
    @api.depends('private_key', 'key_file')
    def _compute_private_key(self):
        for server in self:
            server.private_key = self.execute_local(['cat', server.key_file])

    @api.multi
    @api.depends('public_key', 'key_file')
    def _compute_public_key(self):
        for server in self:
            server.public_key = self.execute_local([
                'cat', '%s.pub' % server.key_file,
            ])

    @api.multi
    def _inverse_private_key(self):
        """
        """
        for server in self:
            name = server.fulldomain
            self.execute_local([
                'mkdir', '-p',
                os.path.join(server.home_directory, '.ssh', 'keys'),
            ])
            key_file = os.path.join(
                server.home_directory, '.ssh', 'keys', name,
            )
            self.execute_write_file(
                key_file, server.private_key, operator='w',
            )
            self.execute_local(['chmod', '600', key_file])

    @api.multi
    def _inverse_public_key(self):
        """
        """
        for server in self:
            key_dir = os.path.join(server.home_directory, '.ssh', 'keys')
            self.execute_local(['mkdir', '-p', key_dir])
            key_file = os.path.join(key_dir, server.fulldomain)
            key_file_pub = '%s.pub' % key_file
            self.execute_write_file(
                key_file_pub, server.public_key, operator='w',
            )
            self.execute_local(['chmod', '600', key_file_pub])

    @property
    def fulldomain(self):
        """
        """

        fulldomain = '%s.%s' % (self.name, self.domain_id.name)
        if self.control_dns and self.domain_id.dns_id:
            ip = socket.gethostbyname(fulldomain)
            if ip != self.ip:
                self.raise_error(
                    'Could not resolve hostname of the server "%s"',
                    fulldomain,
                )
        return fulldomain

    @api.multi
    @api.constrains('name', 'ip')
    def _check_name_ip(self):
        """
        Check that the server domain does not contain any forbidden
        characters.
        """
        if not re.match(r"^[\w\d-]*$", self.name):
            self.raise_error(
                "Name can only contains letters, digits, -",
            )
        if not re.match(r"^[\d:.]*$", self.ip):
            self.raise_error(
                "IP can only contains digits, dots and :",
            )

    @api.multi
    def deploy_ssh_config(self):
        for server in self:
            name = server.fulldomain
            ssh_config = os.path.join(self.home_directory, '.ssh', 'config')
            sed = os.path.join(
                modules.get_module_path('clouder'), 'res', 'sed.sh',
            )
            self.execute_local([sed, name, ssh_config])
            self.execute_write_file(ssh_config, 'Host %s' % name)
            self.execute_write_file(
                ssh_config, '\n  HostName %s' % server.ip,
            )
            self.execute_write_file(
                ssh_config, '\n  Port %s' % server.ssh_port,
            )
            self.execute_write_file(
                ssh_config, '\n  User %s' % (server.login or 'root'),
            )
            self.execute_write_file(
                ssh_config, '\n  IdentityFile ~/.ssh/keys/%s' % name,
            )
            self.execute_write_file(
                ssh_config, '\n#END %s\n' % name,
            )

    @api.model
    def create(self, vals):
        res = super(ClouderServer, self).create(vals)
        # In swarm mode, set master node with current node if not already exist
        if self.runner == 'swarm' and not self.master_id:
            self.env.ref('clouder.clouder_settings').master_id = res.id
        return res

    @api.multi
    def write(self, vals):
        res = super(ClouderServer, self).write(vals)
        self.deploy_ssh_config()
        return res

    @api.multi
    def do(self, name, action, where=False):
        if action == 'deploy_frame':
            self = self.with_context(no_enqueue=True)
        return super(ClouderServer, self).do(name, action, where=where)

    @api.multi
    def start_containers(self):
        self = self.with_context(no_enqueue=True)
        self.do('start_containers', 'start_containers_exec')

    @api.multi
    def start_containers_exec(self):
        """
        Restart all containers of the server.
        """
        containers = self.env['clouder.container'].search(
            [('server_id', '=', self.id)])
        for container in containers:
            container.start()

    @api.multi
    def stop_containers(self):
        self = self.with_context(no_enqueue=True)
        self.do('stop_containers', 'stop_containers_exec')

    @api.multi
    def stop_containers_exec(self):
        """
        Stop all container of the server.
        """
        containers = self.env['clouder.container'].search(
            [('server_id', '=', self.id)])
        for container in containers:
            container.stop()

    @api.multi
    def test_connection(self):
        """
        Test connection to the server.
        """
        self.connect()
        self.raise_error('Connection successful!')

    @api.multi
    def deploy(self):
        """
        """
        self.deploy_ssh_config()
        if self.deployer == 'swarm' and self.master_id == self:
            self.execute(
                ['docker', 'swarm', 'init', '--advertise-addr', self.ip])
        super(ClouderServer, self).deploy()

    @api.multi
    def purge(self):
        """
        """
        super(ClouderServer, self).purge()

    @api.multi
    def deploy_dns(self):
        self = self.with_context(no_enqueue=True)
        self.do('deploy_dns %s' % self.fulldomain, 'deploy_dns_exec')

    @api.multi
    def deploy_dns_exec(self):
        self.purge_dns_exec()

        if self.domain_id.dns_id:
            self.domain_id.dns_id.execute([
                'echo "%s IN A %s" >> "%s"' % (
                    self.name, self.ip, self.domain_id.configfile,
                )
            ])
            self.domain_id.refresh_serial(self.fulldomain)
            # self.control_dns = True

    @api.multi
    def purge_dns(self):
        self = self.with_context(no_enqueue=True)
        self.do('purge_dns', 'purge_dns_exec')

    @api.multi
    def purge_dns_exec(self):
        self.control_dns = False
        if self.domain_id.dns_id:
            self.domain_id.dns_id.execute([
                'sed', '-i', r'"/%s\sIN\sA/d"' % self.name,
                self.domain_id.configfile,
            ])
            self.domain_id.refresh_serial()

    @api.multi
    def oneclick_deploy_element(
            self, type, code, container=False, code_container='', ports=None):

        if not ports:
            ports = []

        application_obj = self.env['clouder.application']
        container_obj = self.env['clouder.container']
        port_obj = self.env['clouder.container.port']
        base_obj = self.env['clouder.base']

        application = application_obj.search([('code', '=', code)])

        if not container and code_container:
            container = container_obj.search([
                ('environment_id', '=', self.environment_id.id),
                ('suffix', '=', code_container)])
        if not container:
            container = container_obj.search([
                ('environment_id', '=', self.environment_id.id),
                ('suffix', '=', code)])

        if type == 'container':
            if not container:
                # ports = []
                # if self.oneclick_ports:
                #     ports = [(0,0,{'name':'bind', 'localport': 53,
                # 'hostport': 53, 'expose': 'internet', 'udp': True})]
                container = container_obj.create({
                    'suffix': code,
                    'environment_id': self.environment_id.id,
                    'server_id': self.id,
                    'application_id': application.id,
                })
                if self.oneclick_ports and ports:
                    for port in ports:
                        port_record = port_obj.search([
                            ('container_id', '=', container.childs['exec'].id),
                            ('localport', '=', port)])
                        port_record.write({'hostport': port})
                    container = container.with_context(container_childs=False)
                    container.childs['exec'].deploy()
            return container

        if type == 'base':
            base = base_obj.search([
                ('name', '=', code), ('domain_id', '=', self.domain_id.id)])
            if not base:
                base = base_obj.create({
                    'name': code,
                    'domain_id': self.domain_id.id,
                    'environment_id': self.environment_id.id,
                    'title': application.name,
                    'application_id': application.id,
                    'container_id': container.id,
                    'admin_name': 'admin',
                    'admin_password': 'adminadmin',
                    'ssl_only': True,
                    'autosave': True,
                })
            return base

        if type == 'subservice':
            if not container_obj.search([
                    ('environment_id', '=', self.environment_id.id),
                    ('suffix', '=', container.name + '-test')]):
                container.reset_base_ids = [
                    (6, 0, [b.id for b in container.base_ids])]
                container.subservice_name = 'test'
                container.install_subservice()

    @api.multi
    def oneclick_deploy(self):
        self = self.with_context(no_enqueue=True)
        self.do('oneclick_deploy', 'oneclick_deploy_exec')

    @api.multi
    def oneclick_deploy_exec(self):
        # TODO check that ns record of the domain is the IP
        return

    @api.multi
    def oneclick_purge(self):
        self = self.with_context(no_enqueue=True)
        self.do('oneclick_purge', 'oneclick_purge_exec')

    @api.multi
    def oneclick_purge_exec(self):
        return

    @api.multi
    def clean(self):
        self = self.with_context(no_enqueue=True)
        self.do('clean', 'clean_exec')

    @api.multi
    def clean_exec(self):
        """
        Clean the server from unused containers / images / volumes.
        http://blog.yohanliyanage.com/2015/05/docker-clean-up-after-yourself/
        """
        self.execute(['docker', 'rmi $(docker images -f "dangling=true" -q)'])
        self.execute(['docker', 'rmi', '-f', '$(docker images -q)'])
        self.execute([
            'docker',
            'run -v /var/run/docker.sock:/var/run/docker.sock '
            '-v /var/lib/docker:/var/lib/docker '
            '--rm martin/docker-cleanup-volumes'])
