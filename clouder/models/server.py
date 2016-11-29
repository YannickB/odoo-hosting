# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

import logging

from openerp import models, fields, api
from openerp import modules

import os.path
import socket
import re

_logger = logging.getLogger(__name__)

try:
    from libcloud.compute.base import NodeAuthSSHKey
    from libcloud.compute.providers import get_driver
    from libcloud.compute.types import Provider
except ImportError:
    _logger.warning('Cannot `import libcloud`.')


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
    public_ip = fields.Char('Public IP')
    private_ip = fields.Char('Private IP')
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
    assign_ip = fields.Boolean(
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
    libcloud_name = fields.Char('Name')
    libcloud_state = fields.Char(
        'State', compute='_compute_libcloud_state')
    libcloud_image = fields.Char('Image')
    # image = fields.Selection(
    # lambda s: s._get_libcloud_images(), string='Image')
    libcloud_size = fields.Selection(
        lambda s: s._get_libcloud_sizes(), string='Size')
    libcloud_location = fields.Selection(
        lambda s: s._get_libcloud_locations(), string='Location')

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

    # @api.multi
    # def _get_libcloud_images(self):
    #     images = []
    #     if 'provider_id' in self.env.context and \
    #             self.env.context['provider_id']:
    #         provider = self.env['clouder.provider'].browse(
    #             self.env.context['provider_id'])
    #         cls = get_driver(getattr(Provider, provider.name))
    #         driver = cls(provider.login, provider.secret_key)
    #
    #         images = [(i.id,i.id) for i in driver.list_images()]
    #     return images

    @api.multi
    def _compute_libcloud_state(self):
        for record in self:
            if record.provider_id:
                nodes = record.libcloud_get_nodes()
                state = 'UNKNOWN'
                for node in nodes:
                    state = node.state
                record.state = state
                _logger.info('%s', state)

    @api.multi
    def _get_libcloud_sizes(self):

        sizes = [('t2.micro', 't2.micro')]
        try:
            provider = self.env['clouder.provider'].browse(
                self.env.context['provider_id'])
            Driver = get_driver(getattr(Provider, provider.name))
            driver = Driver(provider.login, provider.secret_key)

            sizes = [(s.id, s.id) for s in driver.list_sizes()
                     if s.id == 't2.micro']
        except KeyError:
            _logger.debug('provider_id not in context')
        return sizes

    @api.multi
    def _get_libcloud_locations(self):

        locations = [('0', '0')]
        try:
            provider = self.env['clouder.provider'].browse(
                self.env.context['provider_id'])
            Driver = get_driver(getattr(Provider, provider.name))
            driver = Driver(provider.login, provider.secret_key)

            locations = [(l.id, l.id) for l in driver.list_locations()]
            _logger.info('%s', locations)
        except KeyError:
            _logger.debug('provider_id not in context')
        return locations

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
    @api.constrains('name', 'public_ip', 'private_ip')
    def _check_name_ip(self):
        """
        Check that the server domain does not contain any forbidden
        characters.
        """
        if not re.match(r"^[\w\d-]*$", self.name):
            self.raise_error(
                "Name can only contains letters, digits, -",
            )
        if not re.match(r"^[\d:.]*$", self.public_ip):
            self.raise_error(
                "IP can only contains digits, dots and :",
            )
        if not re.match(r"^[\d:.]*$", self.private_ip):
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
                ssh_config, '\n  HostName %s' % server.public_ip,
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
            self.write({'manager': True})
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
    def configure(self):
        self = self.with_context(no_enqueue=True)
        self.do('configure', 'configure_exec')

    @api.multi
    def configure_exec(self):
        """
        Configure server
        """

        # Recover ips from node if libcloud
        if self.provider_id:
            for node in self.libcloud_get_nodes():
                self.write({'public_ip': node.public_ips[0]})
                self.write({'private_ip': node.private_ips[0]})

        # Install Docker
        self.execute(['sudo curl -sSL https://get.docker.com/ | sudo sh'])
        # Add user to Docker group
        self.execute(['sudo usermod -aG docker', self.login])

    @api.multi
    def test_connection(self):
        """
        Test connection to the server.
        """
        self.ensure_one()
        ssh = self.connect()
        with ssh.get_channel():
            self.raise_error('Connection successful!')

    @api.multi
    def deploy(self):
        """
        """
        self.deploy_ssh_config()
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
                    self.name, self.public_ip, self.domain_id.configfile,
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

    @api.multi
    def libcloud_get_nodes(self):
        """
        Return libcloud nodes linked to this record.
        We return a list because in some case we may have several nodes,
        but we should only have one.
        :return:
        """
        Driver = get_driver(getattr(Provider, self.provider_id.name))
        driver = Driver(self.provider_id.login, self.provider_id.secret_key)

        res = []
        for node in driver.list_nodes():
            if node.name == self.libcloud_name and node.state != 'terminated':
                res.append(node)
        return res

    @api.multi
    def libcloud_create(self):
        self = self.with_context(no_enqueue=True)
        self.do('libcloud_create', 'libcloud_create_exec')

    @api.multi
    def libcloud_create_exec(self):

        self.libcloud_destroy_exec()

        Driver = get_driver(getattr(Provider, self.provider_id.name))
        driver = Driver(self.provider_id.login, self.provider_id.secret_key)

        image = [i for i in driver.list_images()
                 if i.id == self.libcloud_image][0]
        size = [s for s in driver.list_sizes()
                if s.id == self.libcloud_size][0]
        location = False
        if self.libcloud_location:
            location = [l for l in driver.list_locations()
                        if l.id == self.libcloud_location][0]

        # Create node
        node = driver.create_node(
            name=self.name, image=image,
            size=size, location=location, ssh_username=self.login or 'root',
            auth=NodeAuthSSHKey(self.public_key))

        # Store name in specific field, in case different from name field
        self.write({'libcloud_name': node.name})

        # Wait until running
        driver.wait_until_running([node])

        # Configure node, install Docker, add to Swarm etc...
        self.configure_exec()

    @api.multi
    def libcloud_destroy(self):
        self = self.with_context(no_enqueue=True)
        self.do('libcloud_destroy', 'libcloud_destroy_exec')

    @api.multi
    def libcloud_destroy_exec(self):
        self.libcloud_get_nodes().destroy()

    @api.multi
    def libcloud_reboot(self):
        self = self.with_context(no_enqueue=True)
        self.do('libcloud_reboot', 'libcloud_reboot_exec')

    @api.multi
    def libcloud_reboot_exec(self):
        Driver = get_driver(getattr(Provider, self.provider_id.name))
        driver = Driver(self.provider_id.login, self.provider_id.secret_key)

        for node in self.libcloud_get_nodes():
            if node.state == 'stopped':
                driver.ex_start_node(node)
            else:
                node.reboot()

    @api.multi
    def libcloud_stop(self):
        self = self.with_context(no_enqueue=True)
        self.do('libcloud_stop', 'libcloud_stop_exec')

    @api.multi
    def libcloud_stop_exec(self):
        Driver = get_driver(getattr(Provider, self.provider_id.name))
        driver = Driver(self.provider_id.login, self.provider_id.secret_key)
        driver.ex_stop_node(n for n in self.libcloud_get_nodes())
