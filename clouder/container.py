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

import model

import re

import time
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class ClouderOneclick(models.Model):

    _name = 'clouder.oneclick'

    name = fields.Char('Nom', required=True)
    function = fields.Char('Function', required=True)


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

    name = fields.Char('Domain name', required=True)
    environment_id = fields.Many2one('clouder.environment', 'Environment',
                                     required=True)
    ip = fields.Char('IP')
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
    supervision_id = fields.Many2one('clouder.container', 'Supervision Server')
    runner_id = fields.Many2one('clouder.container', 'Runner')
    oneclick_id = fields.Many2one('clouder.oneclick', 'Oneclick Deployment')

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

        super(ClouderServer, self).deploy()

        self.execute_local(['mkdir', '-p', self.home_directory + '/.ssh/keys'])
        key_file = self.home_directory + '/.ssh/keys/' + self.name
        self.execute_write_file(key_file, self.private_key)
        self.execute_write_file(key_file + '.pub', self.public_key)
        self.execute_local(['chmod', '700', key_file])
        self.execute_local(['chmod', '700', key_file + '.pub'])
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', 'Host ' + self.name)
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', '\n  HostName ' + self.ip)
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', '\n  Port ' +
                                str(self.ssh_port))
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', '\n  User root')
        self.execute_write_file(self.home_directory + '/.ssh/config',
                                '\n  IdentityFile ~/.ssh/keys/' + self.name)
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
        super(ClouderServer, self).purge()

    @api.multi
    def oneclick_deploy(self):
        getattr(self, self.oneclick_id.function + '_purge')()
        getattr(self, self.oneclick_id.function + '_deploy')()

    @api.multi
    def oneclick_purge(self):
        getattr(self, self.oneclick_id.function + '_purge')()

    @api.multi
    def clean(self):
        """
        Clean the server from unused containers / images / volumes.
        http://blog.yohanliyanage.com/2015/05/docker-clean-up-after-yourself/
        """
#        Too risky?
#        self.execute_local(['docker rm -v $(docker ps -a -q -f status=exited)'])
        self.execute(['docker', 'rmi $(docker images -f "dangling=true" -q)'])
        self.execute(['docker', 'run -v /var/run/docker.sock:/var/run/docker.sock -v /var/lib/docker:/var/lib/docker --rm martin/docker-cleanup-volumes'])


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

    @api.one
    def _get_name(self):
        """
        Return the name of the container
        """
        self.name = self.environment_id.prefix + '-' + self.suffix

    name = fields.Char('Name', compute='_get_name', required=False)
    environment_id = fields.Many2one('clouder.environment', 'Environment',
                                     required=True)
    suffix = fields.Char('Suffix', required=True)
    application_id = fields.Many2one('clouder.application',
                                     'Application', required=True)
    image_id = fields.Many2one('clouder.image', 'Image', required=True)
    server_id = fields.Many2one('clouder.server', 'Server', required=True)
    image_version_id = fields.Many2one('clouder.image.version',
                                       'Image version', required=True)
    time_between_save = fields.Integer('Minutes between each save')
    save_expiration = fields.Integer('Days before save expiration')
    date_next_save = fields.Datetime('Next save planned')
    save_comment = fields.Text('Save Comment')
    autosave = fields.Boolean('Save?')
    port_ids = fields.One2many('clouder.container.port',
                               'container_id', 'Ports')
    volume_ids = fields.One2many('clouder.container.volume',
                                 'container_id', 'Volumes')
    option_ids = fields.One2many('clouder.container.option',
                                 'container_id', 'Options')
    link_ids = fields.One2many('clouder.container.link',
                               'container_id', 'Links')
    base_ids = fields.One2many('clouder.base',
                               'container_id', 'Bases')
    metadata_ids = fields.One2many('clouder.container.metadata', 'container_id', 'Metadata')
    parent_id = fields.Many2one('clouder.container.child', 'Parent')
    child_ids = fields.One2many('clouder.container.child',
                                'container_id', 'Childs')
    subservice_name = fields.Char('Subservice Name')
    ports_string = fields.Text('Ports', compute='_get_ports')
    backup_ids = fields.Many2many(
        'clouder.container', 'clouder_container_backup_rel',
        'container_id', 'backup_id', 'Backup containers')
    public = fields.Boolean('Public?')

    @property
    def fullname(self):
        """
        Property returning the full name of the container.
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
                if link.name.name.check_role('database'):
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
        fullname = self.fullname
        if self.parent_id and not self.child_ids:
            fullname = self.parent_id.container_id.fullname
        db_user = fullname.replace('-', '_').replace('.', '_')
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
    def base_backup_container(self):
        return self

    @property
    def ports(self):
        """
        Property returning the ports linked to this container, in a dict.
        """
        ports = {}
        for child in self.child_ids:
            if child.child_id:
                ports.update(child.child_id.ports)
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
        ('name_uniq', 'unique(server_id,environment_id,name)',
         'Name must be unique per server!'),
    ]

    @api.one
    @api.constrains('suffix')
    def _validate_data(self):
        """
        Check that the container name does not contain any forbidden
        characters.
        """
        if not re.match("^[\w\d-]*$", self.suffix):
            raise except_orm(
                _('Data error!'),
                _("Suffix can only contains letters, digits and dash"))

    @api.one
    @api.constrains('application_id')
    def _check_backup(self):
        """
        Check that a backup server is specified.
        """
        if not self.backup_ids and \
                not self.application_id.check_role('no-backup'):
            raise except_orm(
                _('Data error!'),
                _("You need to create at least one backup container."))

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

    @api.multi
    def onchange_application_id_vals(self, vals):
        """
        Update the options, links and some other fields when we change
        the application_id field.
        """
        if 'application_id' in vals and vals['application_id']:
            application = self.env['clouder.application'].browse(
                vals['application_id'])
            if 'server_id' not in vals or not vals['server_id']:
                vals['server_id'] = application.next_server_id.id
            if not vals['server_id']:
                servers = self.env['clouder.server'].search([])[0]
                if servers:
                    vals['server_id'] = servers[0].id
                else:
                    raise except_orm(
                        _('Data error!'),
                        _("You need to create a server before "
                          "create any container."))

            options = []
            # Getting sources for new options
            option_sources = {x.id: x for x in application.type_id.option_ids}
            sources_to_add = option_sources.keys()
            # Checking old options
            if 'option_ids' in vals:
                for option in vals['option_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(option, (list, tuple)):
                        option = {
                            'name': option[2].get('name', False),
                            'value': option[2].get('value', False)
                        }
                        # This case means we do not have an odoo recordset and need to load the link manually
                        if isinstance(option['name'], int):
                            option['name'] = self.env['clouder.application.type.option'].browse(option['name'])
                    else:
                        option = {
                            'name': getattr(option, 'name', False),
                            'value': getattr(option, 'value', False)
                        }
                    # Keeping the option if there is a match with the sources
                    if option['name'] and option['name'].id in option_sources:
                        option['source'] = option_sources[option['name'].id]

                        if option['source'].type == 'container' and option['source'].auto and \
                                not (option['source'].app_code and option['source'].app_code != application.code):
                            # Updating the default value if there is no current one set
                            options.append((0, 0, {
                                'name': option['source'].id,
                                'value': option['value'] or option['source'].get_default
                            }))

                            # Removing the source id from those to add later
                            sources_to_add.remove(option['name'].id)

            # Adding remaining options from sources
            for def_opt_key in sources_to_add:
                if option_sources[def_opt_key].type == 'container' and option_sources[def_opt_key].auto and \
                        not (
                                    option_sources[def_opt_key].app_code and
                                    option_sources[def_opt_key].app_code != application.code
                        ):
                    options.append((0, 0, {
                            'name': option_sources[def_opt_key].id,
                            'value': option_sources[def_opt_key].get_default
                    }))

            # Replacing old options
            vals['option_ids'] = options

            # Getting sources for new links
            link_sources = {x.id: x for x in application.link_ids}
            sources_to_add = link_sources.keys()
            links_to_process = []
            # Checking old links
            if 'link_ids' in vals:
                for link in vals['link_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(link, (list, tuple)):
                        link = {
                            'name': link[2].get('name', False),
                            'next': link[2].get('next', False)
                        }
                        # This case means we do not have an odoo recordset and need to load the link manually
                        if isinstance(link['name'], int):
                            link['name'] = self.env['clouder.application.link'].browse(link['name'])
                    else:
                        link = {
                            'name': getattr(link, 'name', False),
                            'next': getattr(link, 'next', False)
                        }
                    # Keeping the link if there is a match with the sources
                    if link['name'] and link['name'].id in link_sources:
                        link['source'] = link_sources[link['name'].id]
                        links_to_process.append(link)

                        # Remove used link from sources
                        sources_to_add.remove(link['name'].id)

            # Adding links from source
            for def_key_link in sources_to_add:
                link = {
                    'name': getattr(link_sources[def_key_link], 'name', False),
                    'next': getattr(link_sources[def_key_link], 'next', False),
                    'source': link_sources[def_key_link]
                }
                links_to_process.append(link)

            # Running algorithm to determine new links
            links = []
            for link in links_to_process:
                if link['source'].container and \
                        link['source'].auto or link['source'].make_link:
                    next_id = link['next']
                    if not next_id and \
                            'parent_id' in vals and vals['parent_id']:
                        parent = self.env['clouder.container.child'].browse(
                            vals['parent_id'])
                        for parent_link in parent.container_id.link_ids:
                            if link['source'].name.code == parent_link.name.name.code \
                                    and parent_link.target:
                                next_id = parent_link.target.id
                    context = self.env.context
                    if not next_id and 'container_links' in context:
                        fullcode = link['source'].name.fullcode
                        if fullcode in context['container_links']:
                            next_id = context['container_links'][fullcode]
                    if not next_id:
                        next_id = link['source'].next.id
                    if not next_id:
                        target_ids = self.search([
                            ('application_id.code', '=', link['source'].name.code),
                            ('parent_id', '=', False)])
                        if target_ids:
                            next_id = target_ids[0].id
                    links.append((0, 0, {'name': link['source'].id,
                                         'target': next_id}))
            # Replacing old links
            vals['link_ids'] = links

            childs = []
            # Getting source for childs
            child_sources = {x.id: x for x in application.child_ids}
            sources_to_add = child_sources.keys()

            # Checking for old childs
            if 'child_ids' in vals:
                for child in vals['child_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(child, (list, tuple)):
                        child = {
                            'name': child[2].get('name', False),
                            'sequence': child[2].get('sequence', False),
                            'required': child[2].get('required', False),
                            'server_id': child[2].get('server_id', False)
                        }
                        # This case means we do not have an odoo recordset and need to load links manually
                        if isinstance(child['name'], int):
                            child['name'] = self.env['clouder.application'].browse(child['name'])
                        if isinstance(child['server_id'], int):
                            child['server_id'] = self.env['clouder.server'].browse(child['server_id'])
                    else:
                        child = {
                            'name': getattr(child, 'name', False),
                            'sequence': getattr(child, 'sequence', False),
                            'required': getattr(child, 'required', False),
                            'server_id': getattr(child, 'server_id', False)
                        }
                    if child['name'] and child['name'].id in child_sources:
                        child['source'] = child_sources[child['name'].id]
                        if child['source'].required:
                            childs.append((0, 0, {
                                'name': child['source'].id,
                                'sequence':  child['sequence'],
                                'server_id':
                                    child['server_id'] and
                                    child['server_id'].id or
                                    child['source'].next_server_id.id
                            }))

                        # Removing from sources
                        sources_to_add.remove(child['name'].id)

            # Adding remaining childs from source
            for def_child_key in sources_to_add:
                child = child_sources[def_child_key]
                if child.required:
                    childs.append((0, 0, {
                        'name': child.id,
                        'sequence': child.sequence,
                        'server_id':
                            getattr(child, 'server_id', False) and
                            child.server_id.id or
                            child.next_server_id.id
                    }))

            # Replacing old childs
            vals['child_ids'] = childs

            # Getting metadata
            metadata_vals = []
            metadata_sources = {x.id: x for x in application.metadata_ids}
            sources_to_add = metadata_sources.keys()
            metadata_to_process = []
            if 'metadata_ids' in vals:
                for metadata in vals['metadata_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(metadata, (list, tuple)):
                        metadata = {
                            'name': metadata[2].get('name', False),
                            'value_data': metadata[2].get('value_data', False)
                        }
                        # This case means we do not have an odoo recordset and need to load the link manually
                        if isinstance(metadata['name'], int):
                            metadata['name'] = self.env['clouder.application'].browse(metadata['name'])
                    else:
                        metadata = {
                            'name': getattr(metadata, 'name', False),
                            'value_data': getattr(metadata, 'value_data', False)
                        }
                    # Processing metadata and adding to list
                    if metadata['name'] and metadata['name'].id in metadata_sources:
                        metadata['source'] = metadata_sources[metadata['name'].id]
                        metadata['value_data'] = metadata['value_data'] or metadata['source'].default_value
                        metadata_to_process.append(metadata)

                        # Removing from sources
                        sources_to_add.remove(metadata['name'].id)

            # Adding remaining metadata from source
            for metadata_key in sources_to_add:
                metadata = {
                    'name': getattr(metadata_sources[metadata_key], 'name', False),
                    'value_data': metadata_sources[metadata_key].default_value,
                    'source': metadata_sources[metadata_key]
                }
                metadata_to_process.append(metadata)

            # Processing new metadata
            for metadata in metadata_to_process:
                if metadata['source'].clouder_type == 'container':
                    metadata_vals.append((0, 0, {
                        'name': metadata['source'].id, 'sequence':  metadata['sequence']}))

            # Replacing old metadata
            vals['metadata_ids'] = metadata_vals

            if 'image_id' not in vals or not vals['image_id']:
                vals['image_id'] = application.default_image_id.id

            if 'backup_ids' not in vals or not vals['backup_ids']:
                if application.container_backup_ids:
                    vals['backup_ids'] = [(6, 0, [
                        b.id for b in application.container_backup_ids])]
                else:
                    backups = self.env['clouder.container'].search([
                        ('application_id.type_id.name', '=', 'backup')])
                    if backups:
                        vals['backup_ids'] = [(6, 0, [backups[0].id])]

            vals['autosave'] = application.autosave

            vals['time_between_save'] = \
                application.container_time_between_save
            vals['save_expiration'] = \
                application.container_save_expiration
        return vals

    @api.multi
    @api.onchange('application_id')
    def onchange_application_id(self):
        vals = {
            'application_id': self.application_id.id,
            'server_id': self.server_id.id,
            'option_ids': self.option_ids,
            'link_ids': self.link_ids,
            'child_ids': self.child_ids,
            }
        vals = self.onchange_application_id_vals(vals)
        self.env['clouder.container.option'].search(
            [('container_id', '=', self.id)]).unlink()
        self.env['clouder.container.link'].search(
            [('container_id', '=', self.id)]).unlink()
        self.env['clouder.container.child'].search(
            [('container_id', '=', self.id)]).unlink()
        for key, value in vals.iteritems():
            setattr(self, key, value)

    @api.multi
    def onchange_image_id_vals(self, vals):
        """
        Update the ports and volumes when we change the image_id field.
        """

        server = getattr(self, 'server_id', False) \
            or 'server_id' in vals \
            and self.env['clouder.server'].browse(vals['server_id'])
        if not server:
            return vals

        if 'image_id' in vals and vals['image_id']:
            image = self.env['clouder.image'].browse(vals['image_id'])

            if 'image_version_id' not in vals or not vals['image_version_id']:
                if not image.version_ids:
                    raise except_orm(
                        _('Data error!'),
                        _("You need to build a version for the image " +
                          image.name))
                else:
                    vals['image_version_id'] = image.version_ids[0].id

            ports = []
            nextport = server.start_port
            # Getting sources for new port
            port_sources = {x.name: x for x in image.port_ids}
            sources_to_add = port_sources.keys()
            ports_to_process = []
            # Checking old ports
            if 'port_ids' in vals:
                for port in vals['port_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(port, (list, tuple)):
                        port = {
                            'name': port[2].get('name', False),
                            'hostport': port[2].get('hostport', False),
                            'localport': port[2].get('localport', False),
                            'expose': port[2].get('expose', False),
                            'udp': port[2].get('udp', False)
                        }
                    else:
                        port = {
                            'name': getattr(port, 'name', False),
                            'hostport': getattr(port, 'hostport', False),
                            'localport': getattr(port, 'localport', False),
                            'expose': getattr(port, 'expose', False),
                            'udp': getattr(port, 'udp', False)
                        }
                    # Keeping the port if there is a match with the sources
                    if port['name'] in port_sources:
                        port['source'] = port_sources[port['name']]
                        ports_to_process.append(port)

                        # Remove used port from sources
                        sources_to_add.remove(port['name'])

            # Adding ports from source
            for def_key_port in sources_to_add:
                port = {
                    'name': getattr(port_sources[def_key_port], 'name', False),
                    'hostport': getattr(port_sources[def_key_port], 'hostport', False),
                    'localport': getattr(port_sources[def_key_port], 'localport', False),
                    'expose': getattr(port_sources[def_key_port], 'expose', False),
                    'udp': getattr(port_sources[def_key_port], 'udp', False),
                    'source': port_sources[def_key_port]
                }
                ports_to_process.append(port)

            for port in ports_to_process:
                if not getattr(port, 'hostport', False):
                    port['hostport'] = False
                context = self.env.context
                if 'container_ports' in context:
                    name = port['name']
                    if not port['hostport'] and name in context['container_ports']:
                        port['hostport'] = context['container_ports'][name]
                if not port['hostport']:
                    while not port['hostport'] \
                            and nextport != server.end_port:
                        port_ids = self.env['clouder.container.port'].search(
                            [('hostport', '=', nextport),
                             ('container_id.server_id', '=', server.id)])
                        if not port_ids and not server.execute([
                                'netstat', '-an', '|', 'grep', str(nextport)]):
                            port['hostport'] = nextport
                        nextport += 1
                if not port['hostport']:
                    raise except_orm(
                        _('Data error!'),
                        _("We were not able to assign an hostport to the "
                          "localport " + port['localport'] + ".\n"
                          "If you don't want to assign one manually, make sure you"
                          " fill the port range in the server configuration, and "
                          "that all ports in that range are not already used."))
                if port['expose'] != 'none':
                    ports.append(((0, 0, {
                        'name': port['name'], 'localport': port['localport'],
                        'hostport': port['hostport'],
                        'expose': port['expose'], 'udp': port['udp']})))
            vals['port_ids'] = ports

            volumes = []
            # Getting sources for new volume
            volume_sources = {x.name: x for x in image.volume_ids}
            sources_to_add = volume_sources.keys()
            volumes_to_process = []
            # Checking old volumes
            if 'volume_ids' in vals:
                for volume in vals['volume_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(volume, (list, tuple)):
                        volume = {
                            'name': volume[2].get('name', False),
                            'hostpath': volume[2].get('hostpath', False),
                            'user': volume[2].get('user', False),
                            'readonly': volume[2].get('readonly', False),
                            'nosave': volume[2].get('nosave', False)
                        }
                    else:
                        volume = {
                            'name': getattr(volume, 'name', False),
                            'hostpath': getattr(volume, 'hostpath', False),
                            'user': getattr(volume, 'user', False),
                            'readonly': getattr(volume, 'readonly', False),
                            'nosave': getattr(volume, 'nosave', False)
                        }
                    # Keeping the volume if there is a match with the sources
                    if volume['name'] in volume_sources:
                        volume['source'] = volume_sources[volume['name']]
                        volumes_to_process.append(volume)

                        # Remove used volume from sources
                        sources_to_add.remove(volume['name'])

            # Adding remaining volumes from source
            for def_key_volume in sources_to_add:
                volume = {
                    'name': getattr(volume_sources[def_key_volume], 'name', False),
                    'hostpath': getattr(volume_sources[def_key_volume], 'hostpath', False),
                    'user': getattr(volume_sources[def_key_volume], 'user', False),
                    'readonly': getattr(volume_sources[def_key_volume], 'readonly', False),
                    'nosave': getattr(volume_sources[def_key_volume], 'nosave', False),
                    'source': volume_sources[def_key_volume]
                }
                volumes_to_process.append(volume)

            for volume in volumes_to_process:
                from_id = False
                if 'parent_id' in vals and vals['parent_id']:
                    parent = self.env['clouder.container.child'].browse(
                        vals['parent_id'])
                    if volume['source'].from_code in parent.container_id.childs:
                        from_id = parent.container_id.childs[volume['source'].from_code].id
                volumes.append(((0, 0, {
                    'name': volume['name'],
                    'from_id': from_id,
                    'hostpath': volume['hostpath'],
                    'user': volume['user'],
                    'readonly': volume['readonly'],
                    'nosave': volume['nosave']
                })))
            vals['volume_ids'] = volumes
        return vals

    @api.multi
    @api.onchange('image_id')
    def onchange_image_id(self):
        vals = {
            'image_id': self.image_id.id,
            'port_ids': self.port_ids,
            'volume_ids': self.volume_ids,
            'parent_id': self.parent_id.id
            }
        vals = self.onchange_image_id_vals(vals)
        self.env['clouder.container.port'].search(
            [('container_id', '=', self.id)]).unlink()
        self.env['clouder.container.volume'].search(
            [('container_id', '=', self.id)]).unlink()
        for key, value in vals.iteritems():
            setattr(self, key, value)

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
                childs_priority = child.child_id.check_priority_childs(
                    container)
                if not priority or priority < childs_priority:
                    priority = childs_priority
        return priority

    @api.multi
    def control_priority(self):
        priority = self.image_version_id.check_priority()
        if self.parent_id:
            parent_priority = \
                self.parent_id.container_id.check_priority_childs(self)
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
        vals = self.onchange_application_id_vals(vals)
        vals = self.onchange_image_id_vals(vals)
        return super(ClouderContainer, self).create(vals)

    @api.multi
    def write(self, vals):
        """
        Override write to trigger a reinstall when we change the image version,
        the ports or the volumes.

        :param vals: The values to update
        """
        # version_obj = self.env['clouder.image.version']
        # flag = False
        # if not 'autocreate' in self.env.context:
        #     if 'image_version_id' in vals or 'port_ids' in vals \
        #             or 'volume_ids' in vals:
        #         flag = True
        #         if 'image_version_id' in vals:
        #             new_version = version_obj.browse(vals['image_version_id'])
        #             self = self.with_context(
        #                 save_comment='Before upgrade from ' +
        #                              self.image_version_id.name +
        #                              ' to ' + new_version.name)
        #         else:
        #             self = self.with_context(
        #                 save_comment='Change on port or volumes')
        res = super(ClouderContainer, self).write(vals)
        # if flag:
        #     self.reinstall()
        if 'autosave' in vals:
            self.deploy_links()
        return res

    @api.one
    def unlink(self):
        """
        Override unlink method to remove all services
        and make a save before deleting a container.
        """
        self.base_ids and self.base_ids.unlink()
        self.env['clouder.save'].search([('backup_id', '=', self.id)]).unlink()
        self.env['clouder.image.version'].search(
            [('registry_id', '=', self.id)]).unlink()
        save = self.save(comment='Before unlink', no_enqueue=True)
        if self.parent_id:
            self.parent_id.save_id = save
        return super(ClouderContainer, self).unlink()

    @api.multi
    def reinstall(self):
        """
        Make a save before making a reinstall.
        """
        if 'save_comment' not in self.env.context:
            self = self.with_context(save_comment='Before reinstall')
        self = self.with_context(forcesave=True)
        self.save(no_enqueue=True)
        self = self.with_context(forcesave=False)
        self = self.with_context(nosave=True)
        super(ClouderContainer, self).reinstall()

    @api.multi
    def save(self, comment=False, no_enqueue=False):
        """
        Create a new container save.
        """

        save = False
        now = datetime.now()

        if 'nosave' in self.env.context \
                or (not self.autosave and 'forcesave' not in self.env.context):
            self.log('This base container not be saved '
                     'or the backup isnt configured in conf, '
                     'skipping save container')
            return

        if no_enqueue:
            self = self.with_context(no_enqueue=True)

        for backup_server in self.backup_ids:
            save_vals = {
                'name': self.now_bup + '_' + self.fullname,
                'backup_id': backup_server.id,
                # 'repo_id': self.save_repository_id.id,
                'date_expiration': (now + timedelta(
                    days=self.save_expiration
                    or self.application_id.container_save_expiration
                )).strftime("%Y-%m-%d"),
                'comment': comment or 'Manual',
                #            ''save_comment' in self.env.context
                # and self.env.context['save_comment']
                # or self.save_comment or 'Manual',
                'now_bup': self.now_bup,
                'container_id': self.id,
            }
            save = self.env['clouder.save'].create(save_vals)
        date_next_save = (datetime.now() + timedelta(
            minutes=self.time_between_save
            or self.application_id.container_time_between_save
        )).strftime("%Y-%m-%d %H:%M:%S")
        self.write({'save_comment': False, 'date_next_save': date_next_save})
        return save

    @api.multi
    def hook_deploy_source(self):
        """
        Hook which can be called by submodules to change the source of the image
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
        self = self.with_context(no_enqueue=True)
        super(ClouderContainer, self).deploy()

        if self.child_ids:
            for child in self.child_ids:
                child.deploy()
            return

        ports = []
        volumes = []
        for port in self.port_ids:
            ports.append(port)
        for volume in self.volume_ids:
            volumes.append(volume)

        self.hook_deploy(ports, volumes)

        time.sleep(3)

        self.deploy_post()

        self.start()

        # For shinken
        self.save(comment='First save', no_enqueue=True)

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

        childs = self.env['clouder.container.child'].search(
            [('container_id', '=', self.id)], order='sequence DESC')
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

    @api.multi
    def install_subservice(self):
        """
        Create a subservice and duplicate the bases
        linked to the parent service.
        """
        if not self.subservice_name:
            return

        self = self.with_context(no_enqueue=True)

        subservice_name = self.suffix + '-' + self.subservice_name
        containers = self.search([('suffix', '=', subservice_name),
                                  ('environment_id', '=', self.environment_id.id),
                                  ('server_id', '=', self.server_id.id)])
        containers.unlink()

        links = {}
        for link in self.link_ids:
            links[link.name.name.fullcode] = link.target.id
        self = self.with_context(container_links=links)
        container_vals = {
            'environment_id': self.environment_id.id,
            'suffix': subservice_name,
            'server_id': self.server_id.id,
            'application_id': self.application_id.id,
            'image_version_id': self.image_version_id.id
        }
        subservice = self.create(container_vals)
        for base in self.base_ids:
            subbase_name = self.subservice_name + '-' + base.name
            self = self.with_context(
                save_comment='Duplicate base into ' + subbase_name)
            base.reset_base(subbase_name, container=subservice)
        self.sub_service_name = False


class ClouderContainerPort(models.Model):
    """
    Define the container.port object, used to define the ports which
    will be mapped in the container.
    """

    _name = 'clouder.container.port'

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Char('Name', required=True)
    localport = fields.Char('Local port', required=True)
    hostport = fields.Char('Host port')
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
    name = fields.Char('Path', required=True)
    hostpath = fields.Char('Host path')
    user = fields.Char('System User')
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
    save_id = fields.Many2one('clouder.save', 'Restore this save on deployment')

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
            'environment_id': self.container_id.environment_id.id,
            'suffix': self.container_id.suffix + '-' + self.name.code,
            'parent_id': self.id,
            'application_id': self.name.id,
            'server_id': self.server_id.id or self.container_id.server_id.id
        })
        if self.save_id:
            self.save_id.container_id = self.child_id
            self.save_id.restore()

    @api.multi
    def purge(self):
        self.child_id and self.child_id.unlink()


class ClouderContainerMetadata(models.Model):
    """
    Defines an object to store metadata linked to an application
    """

    _name = 'clouder.container.metadata'

    name = fields.Many2one('clouder.application.metadata', 'Application', ondelete="cascade", required=True)
    container_id = fields.Many2one('clouder.container', 'Container', ondelete="cascade", required=True)
    value_data = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(name, container_id)', 'Metadata must be unique per container!'),
    ]

    @property
    def value(self):
        """
        Property that returns the value formatted by type
        """
        # Computing the function if needed
        val_to_convert = self.value_data
        if self.name.is_function:
            val_to_convert = "{0}".format(getattr(self.container_id, self.name.function)())

        # Empty value
        if not val_to_convert:
            return False

        # value_type cases
        if self.name.value_type == 'int':
            return int(val_to_convert)
        elif self.name.value_type == 'float':
            return float(val_to_convert)
        # Defaults to char
        return str(val_to_convert)

    @api.one
    @api.constrains('name')
    def _check_metadata_type(self):
        """
        Checks that the metadata is intended for containers
        """
        if self.name.clouder_type != 'container':
            raise except_orm(
                _('Container Metadata error!'),
                _("This metadata is intended for {0} only.".format(self.name.clouder_type))
            )

    @api.one
    @api.constrains('name', 'value_data')
    def _check_object(self):
        """
        Checks if the data can be loaded properly
        """
        # In every case: call the value property to see if the metadata can be loaded properly
        try:
            self.value
        except Exception as e:
            # Logging error for reference
            _logger.error(
                "Application Metadata error!\n" +
                "Invalid value for type {0}: \n\t{1}\n".format(self.name.value_type, self.value_data) +
                "Exception raised:\n\tType: {0}\n\tMessage: {1}".format(type(e).__name__, e.message)
            )
            # User display
            raise except_orm(
                _('Application Metadata error!'),
                _("Invalid value for type {0}: \n\t{1}".format(self.name.value_type, self.value_data))
            )
