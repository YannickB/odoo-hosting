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
from openerp import modules

import clouder_model

import re

import time
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class ClouderServer(models.Model):
    """
    Define the server object, which represent the servers
    clouder can connect to.
    """

    _name = 'clouder.server'
    _inherit = ['clouder.model']

    @api.multi
    def _create_key(self):
        """
        Generate a key on the filesystem.
        """
        if not self.env.ref('clouder.clouder_settings').email_sysadmin:
            raise except_orm(
                _('Data error!'),
                _("You need to specify the sysadmin email in configuration"))

        self.execute_local(['mkdir', '/tmp/key_' + self.env.uid])
        self.execute_local(['ssh-keygen', '-t', 'rsa', '-C',
                            self.email_sysadmin, '-f',
                            '/tmp/key_' + self.env.uid + '/key', '-N', ''])
        return True

    @api.multi
    def _destroy_key(self):
        """
        Destroy the key after once we don't need it anymore.
        """
        self.execute_local(['rm', '-rf', '/tmp/key_' + self.env.uid])
        return True

    @api.multi
    def _default_private_key(self):
        """
        Generate a couple of keys visible use on the server form, which
        we can easily add to the server to connect it.
        """
        self = self.env['clouder.server']
        self.env.uid = str(self.env.uid)

        destroy = True
        if not self.local_dir_exist('/tmp/key_' + self.env.uid):
            self._create_key()
            destroy = False

        key = self.execute_local(['cat', '/tmp/key_' + self.env.uid + '/key'])

        if destroy:
            self._destroy_key()
        return key

    @api.multi
    def _default_public_key(self):
        """
        Generate a couple of keys visible use on the server form, which
        we can easily add to the server to connect it.
        """
        self = self.env['clouder.server']
        self.env.uid = str(self.env.uid)

        destroy = True
        if not self.local_dir_exist('/tmp/key_' + self.env.uid):
            self._create_key()
            destroy = False

        key = self.execute_local(['cat',
                                  '/tmp/key_' + self.env.uid + '/key.pub'])

        if destroy:
            self._destroy_key()
        return key

    name = fields.Char('Domain name', size=64, required=True)
    runner_id = fields.Many2one('clouder.container', 'Runner')
    ip = fields.Char('IP', size=64)
    ssh_port = fields.Integer('SSH port')

    private_key = fields.Text(
        'SSH Private Key',
        default=_default_private_key)
    public_key = fields.Text(
        'SSH Public Key',
        default=_default_public_key)
    start_port = fields.Integer('Start Port', required=True)
    end_port = fields.Integer('End Port', required=True)
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.user_partner)
    supervision_id = fields.Many2one('clouder.container', 'Supervision Server')

    _sql_constraints = [
        ('name_uniq', 'unique(name, ssh_port)',
         'Name/SSH must be unique!'),
    ]

    @api.one
    @api.constrains('name', 'ip')
    def _validate_data(self):
        """
        Check that the server domain does not contain any forbidden
        characters.
        """
        if not re.match("^[\w\d.-]*$", self.name):
            raise except_orm(
                _('Data error!'),
                _("Name can only contains letters, digits, - and ."))
        if not re.match("^[\d:.]*$", self.ip):
            raise except_orm(
                _('Data error!'),
                _("IP can only contains digits, dots and :"))

    @api.multi
    def start_containers(self):
        """
        Restart all containers of the server.
        """
        containers = self.env['clouder.container'].search(
            [('server_id', '=', self.id)])
        for container in containers:
            container.start()

    @api.multi
    def stop_containers(self):
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
        ssh = self.connect()
        ssh['ssh'].close()

    @api.multi
    def deploy(self):
        """
        Add the keys in the filesystem and the ssh config.
        """
        self.purge()
        self.execute_local(['mkdir', '-p', self.home_directory + '/.ssh/keys'])
        key_file = self.home_directory + '/.ssh/keys/' + self.name
        self.execute_write_file(key_file, self.private_key)
        self.execute_local(['chmod', '700', key_file])
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', 'Host ' + self.name)
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', '\n  HostName ' + self.ip)
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', '\n  Port ' +
                                str(self.ssh_port))
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', '\n  User root')
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', '\n  IdentityFile ' +
                                self.home_directory + '/.ssh/keys/' +
                                self.name)
        self.execute_write_file(self.home_directory + '/.ssh/config',
                                '\n#END ' + self.name + '\n')

    @api.multi
    def purge(self):
        """
        Remove the keys from the filesystem and the ssh config.
        """
        self.execute_local([modules.get_module_path('clouder') +
                            '/res/sed.sh', self.name,
                            self.home_directory + '/.ssh/config'])
        self.execute_local(['rm', '-rf', self.home_directory +
                            '/.ssh/keys/' + self.name])


class ClouderContainer(models.Model):
    """
    Define the container object, which represent the containers managed by
    the clouder.
    """

    _name = 'clouder.container'
    _inherit = ['clouder.model']

    @api.one
    def _get_ports(self):
        """
        Display the ports on the container lists.
        """
        self.ports_string = ''
        first = True
        for port in self.port_ids:
            if not first:
                self.ports_string += ', '
            if port.hostport:
                self.ports_string += port.name + ' : ' + port.hostport
            first = False

    name = fields.Char('Name', size=64, required=True)
    application_id = fields.Many2one('clouder.application',
                                     'Application', required=True)
    image_id = fields.Many2one('clouder.image', 'Image', required=True)
    server_id = fields.Many2one('clouder.server', 'Server', required=True)
    image_version_id = fields.Many2one('clouder.image.version',
                                       'Image version', required=True)
    save_repository_id = fields.Many2one('clouder.save.repository',
                                         'Save repository')
    time_between_save = fields.Integer('Minutes between each save')
    saverepo_change = fields.Integer('Days before saverepo change')
    saverepo_expiration = fields.Integer('Days before saverepo expiration')
    save_expiration = fields.Integer('Days before save expiration')
    date_next_save = fields.Datetime('Next save planned')
    save_comment = fields.Text('Save Comment')
    nosave = fields.Boolean('No Save?')
    privileged = fields.Boolean('Privileged?')
    port_ids = fields.One2many('clouder.container.port',
                               'container_id', 'Ports')
    volume_ids = fields.One2many('clouder.container.volume',
                                 'container_id', 'Volumes')
    option_ids = fields.One2many('clouder.container.option',
                                 'container_id', 'Options')
    link_ids = fields.One2many('clouder.container.link',
                               'container_id', 'Links')
    service_ids = fields.One2many('clouder.service',
                                  'container_id', 'Services')
    parent_id = fields.Many2one('clouder.container.child', 'Parent')
    child_ids = fields.One2many('clouder.container.child',
                                'container_id', 'Childs')
    ports_string = fields.Text('Ports', compute='_get_ports')
    backup_ids = fields.Many2many(
        'clouder.container', 'clouder_container_backup_rel',
        'container_id', 'backup_id', 'Backup containers')
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.user_partner)
    partner_ids = fields.Many2many(
        'res.partner', 'clouder_container_partner_rel',
        'container_id', 'partner_id', 'Users')

    @property
    def fullname(self):
        """
        Property returning the full name of the server.
        """
        return self.name + '_' + self.server_id.name

    @property
    def volumes_save(self):
        """
        Property returning the all volume path, separated by a comma.
        """
        return ','.join([volume.name for volume in self.volume_ids
                         if not volume.nosave])

    @property
    def root_password(self):
        """
        Property returning the root password of the application
        hosted in this container.
        """
        root_password = ''
        for option in self.option_ids:
            if option.name.name == 'root_password':
                root_password = option.value
        return root_password

    @property
    def database(self):
        """
        Property returning the database container connected to the service.
        """
        database = False
        for link in self.link_ids:
            if link.target:
                if link.name.name.code in ['postgres', 'mysql']:
                    database = link.target
        return database

    @property
    def db_type(self):
        """
        Property returning the database type connected to the service.
        """
        db_type = self.database.application_id.type_id.name
        return db_type

    @property
    def db_server(self):
        """
        Property returning the database server connected to the service.
        """
        if self.database.server_id == self.server_id:
            return self.database.application_id.code
        else:
            return self.database.server_id.name

    @property
    def db_user(self):
        """
        Property returning the database user of the service.
        """
        db_user = self.fullname.replace('-', '_')
        return db_user

    @property
    def db_password(self):
        """
        Property returning the db password of the application
        hosted in this container.
        """
        db_password = ''
        for option in self.option_ids:
            if option.name.name == 'db_password':
                db_password = option.value
        return db_password

    @property
    def ports(self):
        """
        Property returning the ports linked to this container, in a dict.
        """
        ports = {}
        for port in self.port_ids:
            ports[port.name] = {
                'id': port.id, 'name': port.name,
                'hostport': port.hostport, 'localport': port.localport}
        return ports

    @property
    def options(self):
        """
        Property returning a dictionary containing the value of all options
        for this container, even is they are not defined here.
        """
        options = {}
        for option in self.application_id.type_id.option_ids:
            if option.type == 'container':
                options[option.name] = {
                    'id': option.id, 'name': option.id,
                    'value': option.default}
        for option in self.option_ids:
            options[option.name.name] = {
                'id': option.id, 'name': option.name.id, 'value': option.value}
        return options

    @property
    def childs(self):
        """
        Property returning a dictionary containing childs.
        """
        childs = {}
        for child in self.child_ids:
            if child.child_id:
                childs[child.child_id.application_id.code] = child.child_id
        return childs


    _sql_constraints = [
        ('name_uniq', 'unique(server_id,name)',
         'Name must be unique per server!'),
    ]

    @api.one
    @api.constrains('name')
    def _validate_data(self):
        """
        Check that the container name does not contain any forbidden
        characters.
        """
        if not re.match("^[\w\d-]*$", self.name):
            raise except_orm(
                _('Data error!'),
                _("Name can only contains letters, digits and underscore"))

    @api.one
    @api.constrains('application_id')
    def _check_backup(self):
        """
        Check that a backup server is specified.
        """
        if not self.backup_ids and self.application_id.type_id.name \
                not in ['backup', 'backup_upload', 'archive', 'registry', 'openshift']:
            raise except_orm(
                _('Data error!'),
                _("You need to create at least one backup container (it will be automatically assigned)."))

    @api.one
    @api.constrains('image_id', 'image_version_id')
    def _check_config(self):
        """
        Check that a the image of the image version is the same than the image
        of the container.
        """
        if self.image_id.id != self.image_version_id.image_id.id:
            raise except_orm(
                _('Data error!'),
                _("The image of image version must be "
                  "the same than the image of container."))

    @api.one
    @api.constrains('option_ids')
    def _check_option_ids(self):
        """
        Check that the required options are filled.
        """
        for type_option in self.application_id.type_id.option_ids:
            if type_option.type == 'container' and type_option.required:
                test = False
                for option in self.option_ids:
                    if option.name == type_option and option.value:
                        test = True
                if not test:
                    raise except_orm(
                        _('Data error!'),
                        _("You need to specify a value for the option " +
                          type_option.name + " for the container " +
                          self.name + "."))

    @api.one
    @api.constrains('link_ids')
    def _check_link_ids(self):
        """
        Check that the required links are specified.
        """
        for app_link in self.application_id.link_ids:
            if app_link.container and app_link.required:
                test = False
                for link in self.link_ids:
                    if link.name == app_link and link.target:
                        test = True
                if not test:
                    raise except_orm(
                        _('Data error!'),
                        _("You need to specify a link to " + app_link.name.name
                          + " for the container " + self.name))

    @api.multi
    @api.onchange('application_id')
    def onchange_application_id(self):
        """
        Update the options, links and some other fields when we change
        the application_id field.
        """
        if self.application_id:
            if not self.server_id:
                self.server_id = self.application_id.next_server_id

            options = []
            for type_option in self.application_id.type_id.option_ids:
                if type_option.type == 'container' and type_option.auto:
                    if type_option.app_code and type_option.app_code != self.application_id.code:
                        continue
                    test = False
                    for option in self.option_ids:
                        if option.name == type_option:
                            test = True
                    if not test:
                        options.append((0, 0,
                                        {'name': type_option,
                                         'value': type_option.get_default}))
            if not self.option_ids:
                self.option_ids = options

            links = []
            for app_link in self.application_id.link_ids:
                if app_link.container and app_link.auto or app_link.make_link:
                    test = False
                    for link in self.link_ids:
                        if link.name == app_link:
                            test = True
                    if not test:
                        next = False
                        if self.parent_id:
                            for parent_link in self.parent_id.container_id.link_ids:
                                if app_link.name.code == parent_link.name.name.code and parent_link.target:
                                    next = parent_link.target
                        if not next:
                            next = app_link.next
                        links.append((0, 0, {'name': app_link,
                                             'target': next}))
            if not self.link_ids:
                self.link_ids = links

            childs = []
            for child in self.application_id.child_ids:
                if child.required:
                    childs.append((0, 0, {'name': child, 'sequence': child.sequence, 'server_id': child.next_server_id or self.server_id}))
            if not self.child_ids:
                self.child_ids = childs

            if not self.image_id:
                self.image_id = self.application_id.default_image_id

            self.backup_ids = [(6, 0, [
                b.id for b in self.application_id.container_backup_ids])]

            self.time_between_save = \
                self.application_id.container_time_between_save
            self.saverepo_change = \
                self.application_id.container_saverepo_change
            self.saverepo_expiration = \
                self.application_id.container_saverepo_expiration
            self.save_expiration = \
                self.application_id.container_save_expiration

    @api.multi
    @api.onchange('image_id')
    def onchange_image_id(self):
        """
        Update the ports and volumes when we change the image_id field.
        """
        if self.image_id:

            self.privileged = self.application_id.default_image_id.privileged

            if not self.image_version_id:
                self.image_version_id = \
                    self.application_id.default_image_id.version_ids \
                    and self.application_id.default_image_id.version_ids[0]

            ports = []
            for port in self.image_id.port_ids:
                if port.expose != 'none':
                    ports.append(((0, 0, {
                        'name': port.name, 'localport': port.localport,
                        'expose': port.expose, 'udp': port.udp})))
            if not self.port_ids:
                self.port_ids = ports

            volumes = []
            for volume in self.image_id.volume_ids:
                from_id = False
                if volume.from_code in self.parent_id.container_id.childs:
                    from_id = self.parent_id.container_id.childs[volume.from_code]
                volumes.append(((0, 0, {
                    'name': volume.name, 'from_id': from_id, 'hostpath': volume.hostpath,
                    'user': volume.user, 'readonly': volume.readonly,
                    'nosave': volume.nosave})))
            if not self.volume_ids:
                self.volume_ids = volumes

    @api.multi
    def check_priority_childs(self, container):
        priority = False
        for child in self.child_ids:
            if child.child_id == container:
                return False
            if child.child_id:
                child_priority = child.child_id.check_priority()
                if not priority or priority < child_priority:
                    priority = child_priority
                childs_priority = child.child_id.check_priority_childs(container)
                if not priority or priority < childs_priority:
                    priority = childs_priority
        return priority

    @api.multi
    def control_priority(self):
        priority = self.image_version_id.check_priority()
        if self.parent_id:
            parent_priority = self.parent_id.container_id.check_priority_childs(self)
            if not priority or priority < parent_priority:
                priority = parent_priority
        return priority

    @api.multi
    def hook_create(self):
        """
        Add volume/port/link/etc... if not generated through the interface
        """
        if 'autocreate' in self.env.context:
            self.onchange_application_id()
            self.onchange_image_id()
        return super(ClouderContainer, self).hook_create()

    @api.multi
    def create(self, vals):
        if 'application_id' in vals:
            application = self.env['clouder.application'].browse(vals['application_id'])
            if not 'image_id' in vals and application.default_image_id:
                vals['image_id'] = application.default_image_id.id
            if not 'backup_ids' in vals and application.container_backup_ids:
                vals['backup_ids'] = [(6, 0, [
                    b.id for b in application.container_backup_ids])]
            else:
                backups = self.env['clouder.container'].search([('application_id.type_id.name', '=', 'backup')])
                if backups:
                    vals['backup_ids'] = [(6, 0, [backups[0].id])]

        if 'image_id' in vals and not 'image_version_id' in vals:
            image =  self.env['clouder.image'].browse(vals['image_id'])
            if not image.version_ids:
                raise except_orm(
                    _('Data error!'),
                    _("You need to build a version for the image " + image.name))
            vals['image_version_id'] = image.version_ids[0].id

        return super(ClouderContainer, self).create(vals)

    @api.multi
    def write(self, vals):
        """
        Override write to trigger a reinstall when we change the image version,
        the ports or the volumes.

        :param vals: The values to update
        """
        version_obj = self.env['clouder.image.version']
        flag = False
        if not 'autocreate' in self.env.context:
            if 'image_version_id' in vals or 'port_ids' in vals \
                    or 'volume_ids' in vals:
                flag = True
                self = self.with_context(self.create_log('upgrade version'))
                if 'image_version_id' in vals:
                    new_version = version_obj.browse(vals['image_version_id'])
                    self = self.with_context(
                        save_comment='Before upgrade from ' +
                                     self.image_version_id.name +
                                     ' to ' + new_version.name)
                else:
                    self = self.with_context(
                        save_comment='Change on port or volumes')
        res = super(ClouderContainer, self).write(vals)
        if flag:
            self.reinstall()
            self.end_log()
        if 'nosave' in vals:
            self.deploy_links()
        return res

    @api.one
    def unlink(self):
        """
        Override unlink method to remove all services
        and make a save before deleting a container.
        """
        self.service_ids and self.service_ids.unlink()
        self = self.with_context(save_comment='Before unlink')
        self.save()
        return super(ClouderContainer, self).unlink()

    @api.multi
    def reinstall(self):
        """
        Make a save before making a reinstall.
        """
        if not 'save_comment' in self.env.context:
            self = self.with_context(save_comment='Before reinstall')
        self = self.with_context(forcesave=True)
        self.save()
        self = self.with_context(forcesave=False)
        self = self.with_context(nosave=True)
        super(ClouderContainer, self).reinstall()

    @api.multi
    def save(self):
        """
        Create a new container save.
        """
        return
        save = False
        now = datetime.now()
        repo_obj = self.env['clouder.save.repository']

        if not self.save_repository_id:
            repo_ids = repo_obj.search(
                [('container_name', '=', self.name),
                 ('container_server', '=', self.server_id.name)])
            if repo_ids:
                self.save_repository_id = repo_ids[0]

        if not self.save_repository_id \
                or datetime.strptime(self.save_repository_id.date_change,
                                     "%Y-%m-%d") < now or False:
            repo_vals = {
                'name': now.strftime("%Y-%m-%d") + '_' +
                self.name + '_' + self.server_id.name,
                'type': 'container',
                'date_change': (now + timedelta(
                    days=self.saverepo_change
                        or self.application_id.container_saverepo_change
                )).strftime("%Y-%m-%d"),
                'date_expiration': (now + timedelta(
                    days=self.saverepo_expiration
                    or self.application_id.container_saverepo_expiration
                )).strftime("%Y-%m-%d"),
                'container_name': self.name,
                'container_server': self.server_id.name,
            }
            repo_id = repo_obj.create(repo_vals)
            self.save_repository_id = repo_id

        if 'nosave' in self.env.context \
                or (self.nosave and not 'forcesave' in self.env.context):
            self.log('This base container not be saved '
                     'or the backup isnt configured in conf, '
                     'skipping save container')
            return

        for backup_server in self.backup_ids:
            save_vals = {
                'name': self.now_bup + '_' + self.fullname,
                'backup_id': backup_server.id,
                'repo_id': self.save_repository_id.id,
                'date_expiration': (now + timedelta(
                    days=self.save_expiration
                    or self.application_id.container_save_expiration
                )).strftime("%Y-%m-%d"),
                'comment': 'save_comment' in self.env.context
                           and self.env.context['save_comment']
                           or self.save_comment or 'Manual',
                'now_bup': self.now_bup,
                'container_id': self.id,
            }
            save = self.env['clouder.save.save'].create(save_vals)
        date_next_save = (datetime.now() + timedelta(
            minutes=self.time_between_save
            or self.application_id.container_time_between_save
        )).strftime("%Y-%m-%d %H:%M:%S")
        self.write({'save_comment': False, 'date_next_save': date_next_save})
        return save

    @api.multi
    def hook_deploy_source(self):
        """
        Hook which can be called by submodules to change the source of the image.
        """
        return

    @api.multi
    def hook_deploy(self, ports, volumes):
        """
        Hook which can be called by submodules to execute commands to
        deploy a container.
        """
        return

    @api.multi
    def deploy_post(self):
        """
        Hook which can be called by submodules to execute commands after we
        deployed a container.
        """
        return

    @api.multi
    def deploy(self):
        """
        Deploy the container in the server.
        """
        super(ClouderContainer, self).deploy()

        if self.child_ids:
            for child in self.child_ids:
                child.deploy()
        else:
            ports = []
            volumes = []
            nextport = self.server_id.start_port
            for port in self.port_ids:
                if not port.hostport:
                    while not port.hostport \
                            and nextport != self.server_id.end_port:
                        port_ids = self.env['clouder.container.port'].search(
                            [('hostport', '=', nextport),
                             ('container_id.server_id', '=', self.server_id.id)])
                        if not port_ids and not self.server_id.execute([
                                'netstat', '-an', '|', 'grep', str(nextport)]):
                            port.hostport = nextport
                        nextport += 1
                if not port.hostport:
                    raise except_orm(
                        _('Data error!'),
                        _("We were not able to assign an hostport to the "
                          "localport " + port.localport + ".\n"
                          "If you don't want to assign one manually, make sure you"
                          " fill the port range in the server configuration, and "
                          "that all ports in that range are not already used."))
                ports.append(port)
            for volume in self.volume_ids:
                volumes.append(volume)

            self.hook_deploy(ports, volumes)

            time.sleep(3)

            self.deploy_post()

            self.start()

            #For shinken
            self.save()

            self.deploy_links()

        return

    @api.multi
    def hook_purge(self):
        """
        Hook which can be called by submodules to execute commands to
        purge a container.
        """
        return

    @api.multi
    def purge(self):
        """
        Remove the container.
        """

        childs = self.env['clouder.container.child'].search([('container_id','=',self.id)], order='sequence DESC')
        if childs:
            for child in childs:
                child.purge()
        else:
            self.stop()
            self.hook_purge()
        super(ClouderContainer, self).purge()

        return

    @api.multi
    def stop(self):
        """
        Stop the container.
        """

        return


    @api.multi
    def start(self):
        """
        Restart the container.
        """
        self.stop()
        return


class ClouderContainerPort(models.Model):
    """
    Define the container.port object, used to define the ports which
    will be mapped in the container.
    """

    _name = 'clouder.container.port'

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Char('Name', size=64, required=True)
    localport = fields.Char('Local port', size=12, required=True)
    hostport = fields.Char('Host port', size=12)
    expose = fields.Selection(
        [('internet', 'Internet'), ('local', 'Local')], 'Expose?',
        required=True, default='local')
    udp = fields.Boolean('UDP?')

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)',
         'Port name must be unique per container!'),
    ]


class ClouderContainerVolume(models.Model):
    """
    Define the container.volume object, used to define the volume which
    will be saved in the container or will be linked to a directory
    in the host server.
    """

    _name = 'clouder.container.volume'

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    from_id = fields.Many2one('clouder.container', 'From')
    name = fields.Char('Path', size=128, required=True)
    hostpath = fields.Char('Host path', size=128)
    user = fields.Char('System User', size=64)
    readonly = fields.Boolean('Readonly?')
    nosave = fields.Boolean('No save?')

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)',
         'Volume name must be unique per container!'),
    ]


class ClouderContainerOption(models.Model):
    """
    Define the container.option object, used to define custom values
    specific to a container.
    """

    _name = 'clouder.container.option'

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Many2one(
        'clouder.application.type.option', 'Option', required=True)
    value = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)',
         'Option name must be unique per container!'),
    ]

    @api.one
    @api.constrains('container_id')
    def _check_required(self):
        """
        Check that we specify a value for the option
        if this option is required.
        """
        if self.name.required and not self.value:
            raise except_orm(
                _('Data error!'),
                _("You need to specify a value for the option " +
                  self.name.name + " for the container " +
                  self.container_id.name + "."))


class ClouderContainerLink(models.Model):
    """
    Define the container.link object, used to specify the applications linked
    to a container.
    """

    _name = 'clouder.container.link'
    _inherit = ['clouder.model']
    _autodeploy = False

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Many2one(
        'clouder.application.link', 'Application Link', required=True)
    target = fields.Many2one('clouder.container', 'Target')
    deployed = fields.Boolean('Deployed?', readonly=True)

    @api.one
    @api.constrains('container_id')
    def _check_required(self):
        """
        Check that we specify a value for the link
        if this link is required.
        """
        if self.name.required and not self.target:
            raise except_orm(
                _('Data error!'),
                _("You need to specify a link to " +
                  self.name.name.name + " for the container " +
                  self.container_id.name))

    @api.multi
    def deploy_link(self):
        """
        Hook which can be called by submodules to execute commands when we
        deploy a link.
        """
        self.deployed = True
        return

    @api.multi
    def purge_link(self):
        """
        Hook which can be called by submodules to execute commands when we
        purge a link.
        """
        self.deployed = False
        return

    @api.multi
    def control(self):
        """
        Make the control to know if we can launch the deploy/purge.
        """
        if not self.target:
            self.log('The target isnt configured in the link, '
                     'skipping deploy link')
            return False
        if not self.name.container:
            self.log('This application isnt for container, '
                     'skipping deploy link')
            return False
        return True

    @api.multi
    def deploy_(self):
        """
        Control and call the hook to deploy the link.
        """
        self.purge_()
        self.control() and self.deploy_link()

    @api.multi
    def purge_(self):
        """
        Control and call the hook to purge the link.
        """
        self.control() and self.purge_link()


class ClouderContainerChild(models.Model):
    """
    Define the container.link object, used to specify the applications linked
    to a container.
    """

    _name = 'clouder.container.child'

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Many2one(
        'clouder.application', 'Application', required=True)
    sequence = fields.Integer('Sequence')
    server_id = fields.Many2one(
        'clouder.server', 'Server')
    child_id = fields.Many2one(
        'clouder.container', 'Container')

    _order = 'sequence'

    @api.one
    @api.constrains('child_id')
    def _check_child_id(self):
        if self.child_id and not self.child_id.parent_id == self:
            raise except_orm(
                _('Data error!'),
                _("The child container is not correctly linked to the parent"))

    @api.multi
    def deploy(self):
        self = self.with_context(autocreate=True)
        self.purge()
        self.child_id = self.env['clouder.container'].create({
            'name': self.container_id.name + '-' + self.name.code,
            'parent_id': self.id,
            'application_id': self.name.id,
            'server_id': self.server_id.id
        })

    @api.multi
    def purge(self):
        self.child_id and self.child_id.unlink()