# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from openerp import models, fields, api

import re

import time
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class ClouderContainer(models.Model):
    """
    Define the container object, which represent the containers managed by
    the clouder.
    """

    _name = 'clouder.container'
    _inherit = ['clouder.model']
    _sql_constraints = [
        ('name_uniq', 'unique(server_id,environment_id,suffix)',
         'Name must be unique per server!'),
    ]

    name = fields.Char('Name', compute='_compute_name', required=False)
    environment_id = fields.Many2one('clouder.environment', 'Environment',
                                     required=True)
    suffix = fields.Char('Suffix', required=True)
    application_id = fields.Many2one('clouder.application',
                                     'Application', required=True)
    image_id = fields.Many2one('clouder.image', 'Image', required=False)
    server_id = fields.Many2one('clouder.server', 'Server', required=True)
    image_version_id = fields.Many2one('clouder.image.version',
                                       'Image version', required=False)
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
    metadata_ids = fields.One2many(
        'clouder.container.metadata', 'container_id', 'Metadata')
    parent_id = fields.Many2one('clouder.container.child', 'Parent')
    child_ids = fields.One2many('clouder.container.child',
                                'container_id', 'Childs')
    from_id = fields.Many2one('clouder.container', 'From')
    subservice_name = fields.Char('Subservice Name')
    ports_string = fields.Text('Ports', compute='_compute_ports')
    reset_base_ids = fields.Many2many(
        'clouder.base', 'clouder_container_reset_base_rel',
        'container_id', 'base_id', 'Bases to duplicate')
    backup_ids = fields.Many2many(
        'clouder.container', 'clouder_container_backup_rel',
        'container_id', 'backup_id', 'Backup containers')
    volumes_from_ids = fields.Many2many(
        'clouder.container', 'clouder_container_volumes_from_rel',
        'container_id', 'from_id', 'Volumes from')
    public = fields.Boolean('Public?')
    scale = fields.Integer('Scale', default=1)
    dummy = fields.Boolean('Dummy?')
    provider_id = fields.Many2one('clouder.provider', 'Provider')

    @api.multi
    def _compute_ports(self):
        """
        Display the ports on the container lists.
        """
        for rec in self:
            rec.ports_string = ''
            first = True
            for port in rec.port_ids:
                if not first:
                    rec.ports_string += ', '
                if port.hostport:
                    rec.ports_string += '%s : %s' % (port.name, port.hostport)
                first = False

    @api.multi
    def _compute_name(self):
        """
        Return the name of the container
        """
        for rec in self:
            rec.name = '%s-%s' % (rec.environment_id.prefix, rec.suffix)

    @property
    def fullname(self):
        """
        Property returning the full name of the container.
        """
        return '%s_%s' % (self.name, self.server_id.fulldomain)

    @property
    def volumes_save(self):
        """
        Property returning the all volume path, separated by a comma.
        """
        return ','.join([
            volume.name for volume in self.volume_ids if not volume.nosave
        ])

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
                if link.name.check_tags(['database']):
                    database = link.target
        return database

    @property
    def db_type(self):
        """
        Property returning the database type connected to the service.
        """
        db_type = self.database and self.database.application_id.type_id.name
        return db_type

    @property
    def db_server(self):
        """
        Property returning the database server connected to the service.
        """
        return self.database.host

    @property
    def host(self):

        if self.runner == 'swarm':
            res = self.name
            if self.childs and 'exec' in self.childs:
                res = self.childs['exec'].name
        elif self.runner == 'engine':
            res = self.application_id.code
        else:
            res = self.server_id.private_ip
        return res

    @property
    def pod(self):
        """
        For swarm, replace container name in system command by
        command which return the first pod of the service.
        :return:
        """
        pod = self.name
        if self.runner == 'swarm':
            pod = "$(docker ps --format={{.Names}} | grep " + self.name + \
                  ". | head -n1 | awk '{print $1;}' | xargs echo -n)"

        return pod

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
        for key, option in self.options.iteritems():
            if key == 'db_password':
                db_password = option['value']
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
        for child in self.child_ids:
            if child.child_id:
                for key, option in child.child_id.options.iteritems():
                    if option['value']:
                        options[key] = option
        for option in self.option_ids:
            options[option.name.name] = {
                'id': option.id, 'name': option.name.id, 'value': option.value}
        return options

    @property
    def links(self):
        """
        Property returning a dictionary containing the value of all links
        for this container.
        """
        links = {}
        for link in self.link_ids:
            links[link.name.code] = link
        return links

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

    @property
    def available_links(self):
        """
        """
        links = {}
        if self.parent_id:
            for code, link in self.parent_id.container_id.links.iteritems():
                if link.target:
                    links[code] = link.target
            for code, child in self.parent_id.container_id.childs.iteritems():
                links[code] = child

        for code, link in self.links.iteritems():
            if link.target:
                links[code] = link.target
        for code, child in self.childs.iteritems():
            links[code] = child
        return links

    @api.multi
    @api.constrains('environment_id')
    def _check_environment(self):
        """
        Check that the environment linked to the container have a prefix.
        """
        if not self.environment_id.prefix:
            self.raise_error(
                "The environment need to have a prefix",
            )

    @api.multi
    @api.constrains('suffix')
    def _check_suffix(self):
        """
        Check that the container name does not contain any forbidden
        characters.
        """
        if not re.match(r"^[\w\d-]*$", self.suffix):
            self.raise_error(
                "Suffix can only contains letters, digits and dash",
            )

    @api.multi
    @api.constrains('application_id')
    def _check_backup(self):
        """
        Check that a backup server is specified.
        """
        if not self.backup_ids and \
                not self.application_id.check_tags(['no-backup']):
            self.raise_error(
                "You need to create at least one backup container.",
            )

    @api.multi
    @api.constrains('image_id', 'image_version_id')
    def _check_config(self):
        """
        Check that a the image of the image version is the same than the image
        of the container.
        """
        if self.image_version_id \
                and self.image_id.id != self.image_version_id.image_id.id:
            self.raise_error(
                "The image of image version must be "
                "the same than the image of container.",
            )

    # @api.one
    # @api.constrains('image_id', 'child_ids')
    # def _check_image(self):
    #     """
    #     """
    #     if not self.image_id and not self.child_ids:
    #         self.raise_error('You need to specify the image!')

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
                    self.raise_error(
                        "You need to create a server before "
                        "creating a container.",
                    )

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
                        # This case means we do not have an odoo recordset
                        # and need to load the link manually
                        if isinstance(option['name'], int):
                            option['name'] = \
                                self.env['clouder.application.type.option'].\
                                browse(option['name'])
                    else:
                        option = {
                            'name': getattr(option, 'name', False),
                            'value': getattr(option, 'value', False)
                        }
                    # Keeping the option if there is a match with the sources
                    if option['name'] and option['name'].id in option_sources:
                        option['source'] = option_sources[option['name'].id]

                        if option['source'].type == 'container' \
                                and option['source'].auto:
                            flag = True
                            for tag in option['source'].tag_ids:
                                if tag not in application.tag_ids:
                                    flag = False
                            if flag:
                                # Updating the default value if there is
                                # no current one set
                                options.append((0, 0, {
                                    'name': option['source'].id,
                                    'value':
                                        option['value'] or
                                        option['source'].get_default
                                }))

                            # Removing the source id from those to add later
                            sources_to_add.remove(option['name'].id)

            # Adding remaining options from sources
            for def_opt_key in sources_to_add:
                if option_sources[def_opt_key].type == 'container' \
                        and option_sources[def_opt_key].auto:
                    flag = True
                    for tag in option_sources[def_opt_key].tag_ids:
                        if tag not in application.tag_ids:
                            flag = False
                    if flag:
                        options.append((0, 0, {
                            'name': option_sources[def_opt_key].id,
                            'value': option_sources[def_opt_key].get_default
                        }))

            # Replacing old options
            vals['option_ids'] = options

            # Getting sources for new links
            link_sources = \
                {x.id: x for code, x in application.links.iteritems()}
            sources_to_add = link_sources.keys()
            links_to_process = []
            # Checking old links
            if 'link_ids' in vals:
                for link in vals['link_ids']:
                    # Standardizing for possible odoo x2m input
                    if isinstance(link, (list, tuple)):
                        link = {
                            'name': link[2].get('name', False),
                            'required': link[2].get('required', False),
                            'auto': link[2].get('auto', False),
                            'make_link': link[2].get('make_link', False),
                            'next': link[2].get('next', False)
                        }
                        # This case means we do not have an odoo recordset
                        # and need to load the link manually
                        if isinstance(link['name'], int):
                            link['name'] = \
                                self.env['clouder.application.link'].\
                                browse(link['name'])
                    else:
                        link = {
                            'name': getattr(link, 'name', False),
                            'required': getattr(link, 'required', False),
                            'auto': getattr(link, 'auto', False),
                            'make_link': getattr(link, 'make_link', False),
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
                    'required': getattr(
                        link_sources[def_key_link], 'required', False),
                    'auto': getattr(link_sources[def_key_link], 'auto', False),
                    'make_link': getattr(
                        link_sources[def_key_link], 'make_link', False),
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
                    if 'parent_id' in vals and vals['parent_id']:
                        parent = self.env['clouder.container.child'].browse(
                            vals['parent_id'])
                        for parent_code, parent_link \
                                in parent.container_id.\
                                available_links.iteritems():
                            if link['source'].name.id == \
                                    parent_link.application_id.id:
                                next_id = parent_link.id
                    context = self.env.context
                    if not next_id and 'container_links' in context:
                        fullcode = link['source'].name.fullcode
                        if fullcode in context['container_links']:
                            next_id = context['container_links'][fullcode]
                    if not next_id:
                        next_id = link['source'].next.id
                    if not next_id:
                        target_ids = self.search([
                            ('application_id', '=', link['source'].name.id)])
                        if target_ids:
                            next_id = target_ids[0].id
                    links.append((0, 0, {'name': link['source'].name.id,
                                         'required': link['source'].required,
                                         'auto': link['source'].auto,
                                         'make_link': link['source'].make_link,
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
                        # This case means we do not have an odoo recordset
                        # and need to load links manually
                        if isinstance(child['name'], int):
                            child['name'] = self.env['clouder.application'].\
                                browse(child['name'])
                        if isinstance(child['server_id'], int):
                            child['server_id'] = self.env['clouder.server'].\
                                browse(child['server_id'])
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
            metadata_sources = {
                x.id: x for x in application.metadata_ids
                if x.clouder_type == 'container'}
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
                        # This case means we do not have an odoo recordset
                        # and need to load the link manually
                        if isinstance(metadata['name'], int):
                            metadata['name'] = \
                                self.env['clouder.application']\
                                .browse(metadata['name'])
                    else:
                        metadata = {
                            'name': getattr(metadata, 'name', False),
                            'value_data': getattr(
                                metadata, 'value_data', False)
                        }
                    # Processing metadata and adding to list
                    if metadata['name'] \
                            and metadata['name'].id in metadata_sources:
                        metadata['source'] = \
                            metadata_sources[metadata['name'].id]
                        metadata['value_data'] = \
                            metadata['value_data'] \
                            or metadata['source'].default_value
                        metadata_to_process.append(metadata)

                        # Removing from sources
                        sources_to_add.remove(metadata['name'].id)

            # Adding remaining metadata from source
            for metadata_key in sources_to_add:
                metadata = {
                    'name': getattr(
                        metadata_sources[metadata_key], 'name', False),
                    'value_data': metadata_sources[metadata_key].default_value,
                    'source': metadata_sources[metadata_key]
                }
                metadata_to_process.append(metadata)

            # Processing new metadata
            for metadata in metadata_to_process:
                if metadata['source'].clouder_type == 'container':
                    metadata_vals.append((0, 0, {
                        'name': metadata['source'].id,
                        'value_data':  metadata['value_data']}))

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
            vals['dummy'] = application.dummy

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
            'metadata_ids': self.metadata_ids,
            'parent_id': self.parent_id and self.parent_id.id or False
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

            if 'application_id' in vals and vals['application_id']:
                application = self.env['clouder.application'].browse(
                    vals['application_id'])
                if 'image_version_id' not in vals \
                        or not vals['image_version_id']:
                    if application.next_image_version_id:
                        vals['image_version_id'] = \
                            application.next_image_version_id.id

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
                            'udp': port[2].get('udp', False),
                            'use_hostport': port[2].get('use_hostport', False)
                        }
                    else:
                        port = {
                            'name': getattr(port, 'name', False),
                            'hostport': getattr(port, 'hostport', False),
                            'localport': getattr(port, 'localport', False),
                            'expose': getattr(port, 'expose', False),
                            'udp': getattr(port, 'udp', False),
                            'use_hostport': getattr(
                                port, 'use_hostport', False)
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
                    'hostport': getattr(
                        port_sources[def_key_port], 'hostport', False),
                    'localport': getattr(
                        port_sources[def_key_port], 'localport', False),
                    'expose': getattr(
                        port_sources[def_key_port], 'expose', False),
                    'udp': getattr(port_sources[def_key_port], 'udp', False),
                    'use_hostport': getattr(
                        port_sources[def_key_port], 'use_hostport', False),
                    'source': port_sources[def_key_port]
                }
                ports_to_process.append(port)

            for port in ports_to_process:
                if not getattr(port, 'hostport', False):
                    port['hostport'] = False
                context = self.env.context
                if 'container_ports' in context:
                    name = port['name']
                    if not port['hostport'] \
                            and name in context['container_ports']:
                        port['hostport'] = context['container_ports'][name]
                if not port['hostport']:
                    while not port['hostport'] \
                            and nextport != server.end_port:
                        port_ids = self.env['clouder.container.port'].search(
                            [('hostport', '=', nextport)])
                        if not port_ids and not server.execute([
                                'netstat', '-an', '|', 'grep',
                                (server.assign_ip and
                                 server.private_ip + ':' or '') +
                                str(nextport)]):
                            port['hostport'] = nextport
                        nextport += 1
                if not port['hostport']:
                    self.raise_error(
                        "We were not able to assign an hostport to the "
                        "localport %s .\n"
                        "If you don't want to assign one manually, "
                        "make sure you fill the port range in the server "
                        "configuration, and that all ports in that range "
                        "are not already used.",
                        port['localport'],
                    )
                if port['expose'] != 'none':
                    localport = port['localport']
                    if port['use_hostport']:
                        localport = port['hostport']
                    ports.append(((0, 0, {
                        'name': port['name'], 'localport': localport,
                        'hostport': port['hostport'],
                        'expose': port['expose'], 'udp': port['udp'],
                        'use_hostport': port['use_hostport']})))
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
                            'localpath': volume[2].get('localpath', False),
                            'hostpath': volume[2].get('hostpath', False),
                            'user': volume[2].get('user', False),
                            'readonly': volume[2].get('readonly', False),
                            'nosave': volume[2].get('nosave', False)
                        }
                    else:
                        volume = {
                            'name': getattr(volume, 'name', False),
                            'localpath': getattr(volume, 'localpath', False),
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
                    'name': getattr(
                        volume_sources[def_key_volume], 'name', False),
                    'localpath': getattr(
                        volume_sources[def_key_volume], 'localpath', False),
                    'hostpath': getattr(
                        volume_sources[def_key_volume], 'hostpath', False),
                    'user': getattr(
                        volume_sources[def_key_volume], 'user', False),
                    'readonly': getattr(
                        volume_sources[def_key_volume], 'readonly', False),
                    'nosave': getattr(
                        volume_sources[def_key_volume], 'nosave', False),
                    'source': volume_sources[def_key_volume]
                }
                volumes_to_process.append(volume)

            for volume in volumes_to_process:
                volumes.append(((0, 0, {
                    'name': volume['name'],
                    'localpath': volume['localpath'],
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

        image = self.env['clouder.image'].browse(vals['image_id'])
        if vals['parent_id'] and image.volumes_from:
            volumes_from = image.volumes_from.split(',')
            targets = []
            for child in self.env['clouder.container.child'].\
                    browse(vals['parent_id']).container_id.child_ids:
                for code in volumes_from:
                    if child.name.check_tags([code]):
                        targets.append(child.child_id)
            vals['volumes_from_ids'] = [(6, 0, [c.id for c in targets])]

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
    def hook_create(self, vals):

        # Make sure one2one relation with
        # parent link is immediately established
        if self._name == 'clouder.container' and 'parent_id' in vals:
            self.env['clouder.container.child'].browse(
                vals['parent_id']).write({'child_id': self.id})

        # Deploy links and childs stored in context
        for child in self.env.context.get('container_childs', []):
            child_vals = child[2]
            child_vals.update({'container_id': self.id})
            self.env['clouder.container.child'].create(child_vals)
        for link in self.env.context.get('container_links', []):
            link_vals = link[2]
            link_vals.update({'container_id': self.id})
            self.env['clouder.container.link'].create(link_vals)

        self = self.with_context(container_childs=[], container_links=[])

        # Refresh self with added one2many
        self = self.browse(self.id)

        # Add volume/port/link/etc... if not generated through the interface
        if 'autocreate' in self.env.context:
            self.onchange_application_id()
            self.onchange_image_id()

        return super(ClouderContainer, self).hook_create(vals)

    @api.multi
    def create(self, vals):
        vals = self.onchange_application_id_vals(vals)
        vals = self.onchange_image_id_vals(vals)

        # Remove childs and add them in context so they are added between
        # create and deploy.
        # We have to do this because they are newid otherwise.
        if vals['child_ids']:
            self = self.with_context(container_childs=vals['child_ids'])
            vals['child_ids'] = []
        if vals['link_ids']:
            self = self.with_context(container_links=vals['link_ids'])
            vals['link_ids'] = []

        res = super(ClouderContainer, self).create(vals)

        # Deploy all links waiting for this type of container
        links = self.env['clouder.container.link'].search([
            ('name', '=', res.application_id.id), ('auto', '=', True),
            ('target', '=', False)])
        links.write({'target': res.id})
        for link in links:
            link.deploy_link()
        links = self.env['clouder.base.link'].search([
            ('name', '=', res.application_id.id),
            ('auto', '=', True), ('target', '=', False)])
        links.write({'target': res.id})
        for link in links:
            link.deploy_link()

        return res

    @api.multi
    def write(self, vals):
        """
        Override write to trigger a reinstall when we change the image version,
        the ports or the volumes.

        Makes it so that the suffix cannot be changed after creation

        :param vals: The values to update
        """
        # version_obj = self.env['clouder.image.version']
        # flag = False
        # if not 'autocreate' in self.env.context:
        #     if 'image_version_id' in vals or 'port_ids' in vals \
        #             or 'volume_ids' in vals:
        #         flag = True
        #         if 'image_version_id' in vals:
        #             ew_version = version_obj.browse(vals['image_version_id'])
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
        if 'suffix' in vals:
            self.raise_error(
                "You cannot modify the suffix "
                "after the container was created."
            )

        if 'autosave' in vals and self.autosave != vals['autosave']:
            self.deploy_links()
        return res

    @api.multi
    def unlink(self):
        """
        Override unlink method to remove all services
        and make a save before deleting a container.
        """
        for container in self:
            container.base_ids and container.base_ids.unlink()
            self.env['clouder.save'].search(
                [('backup_id', '=', container.id)]).unlink()
            self.env['clouder.image.version'].search(
                [('registry_id', '=', container.id)]).unlink()
            self = self.with_context(save_comment='Before unlink')
            save = container.save_exec(no_enqueue=True)
            if container.parent_id:
                container.parent_id.save_id = save
        return super(ClouderContainer, self).unlink()

    @api.multi
    def reinstall(self):
        """
        Make a save before making a reinstall.
        """
        if 'save_comment' not in self.env.context:
            self = self.with_context(save_comment='Before reinstall')
        self.save_exec(no_enqueue=True)
        self = self.with_context(nosave=True)
        super(ClouderContainer, self).reinstall()
        if self.parent_id:
            childs = self.env['clouder.container.child'].search([
                ('container_id', '=', self.parent_id.container_id.id),
                ('sequence', '>', self.parent_id.sequence)])
            for child in childs:
                if child.child_id:
                    child.child_id.start()

    @api.multi
    def update(self):
        self.do('update', 'update_exec')

    @api.multi
    def update_exec(self):
        containers = [self]
        for child in self.child_ids:
            if child.child_id:
                containers.append(child.child_id)

        bases = {}
        for container in containers:
            if container.application_id.update_strategy != 'never':
                container.reinstall()
                if container.application_id.update_bases:
                    for base in self.base_ids:
                        bases[base.id] = base
                    if self.parent_id:
                        for base in self.parent_id.container_id.base_ids:
                            bases[base.id] = base
        for base_id, base in bases.iteritems():
            base.update_exec()

    @api.multi
    def save(self):
        self.do('save', 'save_exec')

    @api.multi
    def save_exec(self, no_enqueue=False, forcesave=False):
        """
        Create a new container save.
        """

        save = False
        now = datetime.now()

        if forcesave:
            self = self.with_context(forcesave=True)

        if no_enqueue:
            self = self.with_context(no_enqueue=True)

        if 'nosave' in self.env.context \
                or (not self.autosave and 'forcesave' not in self.env.context):
            self.log('This container shall not be saved '
                     'or the backup isnt configured in conf, '
                     'skipping save container')
            return

        for backup_server in self.backup_ids:
            save_vals = {
                'name': self.now_bup + '_' + self.fullname,
                'backup_id': backup_server.id,
                # 'repo_id': self.save_repository_id.id,
                'date_expiration': (now + timedelta(
                    days=self.save_expiration or
                    self.application_id.container_save_expiration
                )).strftime("%Y-%m-%d"),
                'comment': 'save_comment' in self.env.context and
                           self.env.context['save_comment'] or
                           self.save_comment or 'Manual',
                #            ''save_comment' in self.env.context
                # and self.env.context['save_comment']
                # or self.save_comment or 'Manual',
                'now_bup': self.now_bup,
                'container_id': self.id,
            }
            save = self.env['clouder.save'].create(save_vals)
        date_next_save = (datetime.now() + timedelta(
            minutes=self.time_between_save or
            self.application_id.container_time_between_save
        )).strftime("%Y-%m-%d %H:%M:%S")
        self.write({'save_comment': False, 'date_next_save': date_next_save})
        return save

    @api.multi
    def hook_deploy_source(self):
        """
        Hook which can be called by submodules
        to change the source of the image
        """
        return

    @api.multi
    def hook_deploy_compose(self):
        """
        Hook which can be called by submodules to execute commands to
        deploy a set of containers.
        """
        return

    @api.multi
    def hook_deploy_one(self):
        """
        Hook which can be called by submodules to execute commands to
        deploy a container.
        """
        return

    @api.multi
    def get_container_res(self):
        ports = []
        expose_ports = []
        for port in self.port_ids:
            if self.runner != 'swarm':
                ip = ''
                if self.server_id.assign_ip \
                        and self.application_id.type_id.name != 'registry':
                    ip = self.server_id.public_ip + ':'

                ports.append('%s:%s'
                             % (ip + str(port.hostport),
                                port.localport + (port.udp and '/udp' or '')))

            else:
                # Expose port on the swarm only if expose to internet
                if port.expose == 'internet':
                    ports.append(str(port.hostport) + ':' + port.localport)
            if port.use_hostport:
                expose_ports.append(port.hostport)
        volumes = []
        for volume in self.volume_ids:
            if self.runner != 'swarm':
                if volume.hostpath:
                    arg = volume.hostpath + ':' + volume.localpath
                    if volume.readonly:
                        arg += ':ro'
                    volumes.append(arg)
            else:
                volumes.append(
                    'type=volume,source=%s-%s,destination=%s'
                    % (self.name, volume.name, volume.localpath))
        volumes_from = []
        for volume_from in self.volumes_from_ids:
            if self.runner != 'swarm':
                # If not swarm, only return the name of the container
                volumes_from.append(volume_from.name)
            else:
                # If swarm, return all volumes of container
                for volume in volume_from.volume_ids:
                    volumes_from.append(
                        'type=volume,source=%s-%s,destination=%s'
                        % (volume_from.name, volume.name, volume.localpath))
        links = []
        for link in self.link_ids:
            if link.make_link:
                target = link.target
                if 'exec' in target.childs:
                    target = target.childs['exec']
                if self.runner != 'swarm':
                    links.append({'name': target.name, 'code': link.name.code})
                else:
                    # If swarm, return network of linked container
                    if target.environment_id != self.environment_id:
                        network = self.environment_id.prefix + '-network'
                        if network not in links:
                            links.append(network)

        # Get name without compose prefix
        compose_name = self.name
        if 'prefix' in self.env.context:
            compose_name = self.name.replace(self.env.context['prefix'], '')

        return {
            'self': self, 'compose_name': compose_name,
            'ports': ports, 'expose_ports': expose_ports,
            'volumes': volumes, 'volumes_from': volumes_from,
            'links': links, 'environment': {}}

    @api.multi
    def get_container_compose_res(self):
        """
        Recursively build data needed for compose file
        """
        res = []

        # If root, the project name is container name
        if 'prefix' not in self.env.context:
            self = self.with_context(prefix=self.name + '-')

        # Only add service if service without children
        if not self.child_ids:
            res.append(self.get_container_res())

        # Recursively add services from children
        for child in self.child_ids:
            if child.child_id:
                res.extend(child.child_id.get_container_compose_res())

        services = {}
        for service in res:
            services[service['self'].name] = service

        # Replace service name by name without project name
        res_final = []
        for service in res:
            links = []
            for link in service['links']:
                if link['name'] in services:
                    link['name'] = services[link['name']]['compose_name']
                links.append('%s:%s' % (link['name'], link['code']))
            service['links'] = links

            volumes_from = []
            for volume_from in service['volumes_from']:
                if volume_from in services:
                    volume_from = services[volume_from]['compose_name']
                volumes_from.append(volume_from)
            service['volumes_from'] = volumes_from

            res_final.append(service)

        return res_final

    @api.multi
    def deploy_post(self):
        """
        Hook which can be called by submodules to execute commands after we
        deployed a container.
        """
        return

    @api.multi
    def recursive_deploy_one(self):
        """
        Recursively deploy containers one by one
        """

        if self.child_ids:
            self.child_ids.mapped('child_id').recursive_deploy_one()
        else:
            # We only call the hook if service without children
            self.hook_deploy_one()
        return

    @api.multi
    def recursive_deploy_post(self):
        """
        Recursively execute deploy_post function
        """
        if self.child_ids:
            self.child_ids.mapped('child_id').recursive_deploy_post()
        else:
            # We only call the hook if service without children
            self.deploy_post()
        return

    @api.multi
    def recursive_save(self):
        """
        Recursively execute save
        """
        if self.child_ids:
            self.child_ids.mapped('child_id').recursive_save()
        else:
            # Avoid backup alert on monitoring
            self = self.with_context(save_comment='First save')
            self.save_exec(no_enqueue=True)
        return

    @api.multi
    def deploy(self):
        """
        Deploy the container in the server.
        """

        self = self.with_context(no_enqueue=True)
        super(ClouderContainer, self).deploy()

        # Create childs
        if self.child_ids:
            for child in self.child_ids:
                # Childs does not execute deploy when initiated by parent
                child = child.with_context(no_deploy=True)
                child.create_child_exec()

        # Skip deploy if not a real service
        if self.dummy:
            return

        # Skip deploy if compose context and not root
        if 'no_deploy' in self.env.context:
            return

        if self.parent_id:
            self.parent_id.child_id = self

        # If compose mode, we only execute deploy for root
        if self.compose:
            if not self.parent_id:
                self.hook_deploy_compose()
        # If not compose mode, execute deploy for all children
        else:
            self.recursive_deploy_one()

        time.sleep(3)

        # Execute deploy post on all children
        self.recursive_deploy_post()

        # Restart all children
        self.start()

        # Save all children, to avoid monitoring alert before daily cron
        self.recursive_save()

        return

    @api.multi
    def hook_purge_compose(self):
        """
        Hook which can be called by submodules to execute commands to
        purge a container compose.
        """
        return

    @api.multi
    def hook_purge_one(self):
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
            # If compose mode, purge if root
            if self.compose and not self.parent_id:
                self.hook_purge_compose()
            # Recursively delete childs in Odoo
            childs.delete_child_exec()
        else:
            # If not compose, purge current container
            if not self.compose:
                self.stop()
                # self.purge_salt()
                self.hook_purge_one()
        super(ClouderContainer, self).purge()

        return

    @api.multi
    def stop(self):
        self = self.with_context(no_enqueue=True)
        self.do('stop', 'stop_exec')

    @api.multi
    def stop_exec(self):
        """
        Stop the container.
        """
        return

    @api.multi
    def start(self):
        self = self.with_context(no_enqueue=True)
        self.do('start', 'start_exec')

    @api.multi
    def start_exec(self):
        """
        Restart the container.
        """
        self.stop_exec()
        return

    @api.multi
    def install_subservice(self):
        self = self.with_context(no_enqueue=True)
        self.do(
            'install_subservice ' + self.suffix + '-' + self.subservice_name,
            'install_subservice_exec')

    @api.multi
    def install_subservice_exec(self):
        """
        Create a subservice and duplicate the bases
        linked to the parent service.
        """
        if not self.subservice_name:
            return

        self = self.with_context(no_enqueue=True)

        subservice_name = self.suffix + '-' + self.subservice_name
        containers = self.search([
            ('suffix', '=', subservice_name),
            ('environment_id', '=', self.environment_id.id),
            ('server_id', '=', self.server_id.id)])
        for container in containers:
            if container.parent_id:
                container.parent_id.unlink()
        containers.unlink()

        parent = False
        if self.parent_id:
            parent = self.env['clouder.container.child'].create({
                'container_id': self.parent_id.container_id.id,
                'name': self.parent_id.name.id,
                'sequence': self.parent_id.sequence + 1
            })

        links = {}
        for link in self.link_ids:
            links[link.name.fullcode] = link.target.id
        self = self.with_context(container_links=links)
        container_vals = {
            'environment_id': self.environment_id.id,
            'suffix': subservice_name,
            'server_id': self.server_id.id,
            'application_id': self.application_id.id,
            'parent_id': parent and parent.id,
            'from_id': self.id,
            'image_version_id': self.image_version_id.id
        }
        subservice = self.create(container_vals)

        if parent:
            parent.target = subservice

        for base in self.reset_base_ids:
            subbase_name = self.subservice_name + '-' + base.name
            base = base.with_context(
                save_comment='Duplicate base into ' + subbase_name,
                reset_base_name=subbase_name, reset_container=subservice)
            base.reset_base_exec()
        self.subservice_name = False
