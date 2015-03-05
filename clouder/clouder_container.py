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

from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from openerp import modules
import re

import time
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class ClouderServer(models.Model):
    _name = 'clouder.server'
    _inherit = ['clouder.model']

    @api.multi
    def _create_key(self):

        if not self.env.ref('clouder.clouder_settings').email_sysadmin:
            raise except_orm(_('Data error!'),
                _("You need to specify the sysadmin email in configuration"))

        self.execute_local(['mkdir', '/tmp/key_' + self.env.uid])
        self.execute_local(['ssh-keygen', '-t', 'rsa', '-C',
                            self.email_sysadmin, '-f',
                            '/tmp/key_' + self.env.uid + '/key', '-N', ''])
        return True

    @api.multi
    def _destroy_key(self):
        self.execute_local(['rm', '-rf', '/tmp/key_' + self.env.uid])
        return True

    @api.multi
    def _default_private_key(self):
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
    ip = fields.Char('IP', size=64, required=True)
    ssh_port = fields.Integer('SSH port', required=True)

    private_key = fields.Text(
        'SSH Private Key', required=True,
        default=_default_private_key)
    public_key = fields.Text(
        'SSH Public Key', required=True,
        default=_default_public_key)
    start_port = fields.Integer('Start Port', required=True)
    end_port = fields.Integer('End Port', required=True)
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.user_partner)
    supervision_id = fields.Many2one('clouder.container', 'Supervision Server')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    @api.one
    @api.constrains('name', 'ip')
    def _validate_data(self) :
        if not re.match("^[\w\d.-]*$", self.name):
            raise except_orm(
                _('Data error!'),
                _("Name can only contains letters, digits, - and ."))
        if not re.match("^[\d:.]*$", self.ip):
            raise except_orm(
                _('Data error!'),
                _("Admin name can only contains digits, dots and :"))

    # @api.multi
    # def get_vals(self):
    #
    #     vals ={}
    #
    #     vals.update(self.env.ref('clouder.clouder_settings').get_vals())
    #
    #     vals.update({
    #         'server_id': self.id,
    #         'server_domain': self.name,
    #         'server_ip': self.ip,
    #         'server_ssh_port': int(self.ssh_port),
    #         'server_mysql_passwd': self.mysql_passwd,
    #         'server_shinken_configfile': '/usr/local/shinken/etc/hosts/' + self.name + '.cfg',
    #         'server_private_key': self.private_key,
    #         'server_public_key': self.public_key,
    #         'server_start_port': self.start_port,
    #         'server_end_port': self.end_port,
    #     })
    #     return vals

    @api.multi
    def start_containers(self):
        self.env['clouder.container'].search(
            [('server_id', '=', self.id)]).start()

    @api.multi
    def stop_containers(self):
        self.env['clouder.container'].search(
            [('server_id', '=', self.id)]).stop()

    @api.multi
    def deploy(self):
        self.purge()
        key_file = self.home_directory + '/.ssh/keys/' + self.name
        self.execute_write_file(key_file, self.private_key)
        self.execute_local(['chmod', '700', key_file])
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', 'Host ' + self.name)
        self.execute_write_file(self.home_directory +
                                '/.ssh/config', '\n  HostName ' + self.name)
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
        self.execute_local([modules.get_module_path('clouder') +
                            '/res/sed.sh', self.name,
                            self.home_directory + '/.ssh/config'])
        self.execute_local(['rm', '-rf', self.home_directory +
                            '/.ssh/keys/' + self.name])


class ClouderContainer(models.Model):
    _name = 'clouder.container'
    _inherit = ['clouder.model']

    @api.multi
    def _get_ports(self):
        self.ports = ''
        first = True
        for port in self.port_ids:
            if not first:
                self.ports += ', '
            if port.hostport:
                self.ports += port.name + ' : ' + port.hostport
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
    ports = fields.Text('Ports', compute='_get_ports')
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
        return self.name + '_' + self.server_id.name

    @property
    def volumes_save(self):
        return ','.join([volume.name for volume in self.volume_ids
                         if not volume.nosave])

    @property
    def ssh_port(self):
        hostport = 22
        for port in self.port_ids:
            if port.name == 'ssh':
                hostport = port.hostport
        return hostport

    @property
    def root_password(self):
        return (option.value for option in self.option_ids
                if option.name == 'root_password')

    @property
    def options(self):
        options = {}
        for option in self.application_id.type_id.option_ids:
            if option.type == 'container':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in self.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}
        return options

    _sql_constraints = [
        ('name_uniq', 'unique(server_id,name)',
         'Name must be unique per server!'),
    ]

    @api.one
    @api.constrains('name')
    def _validate_data(self):
        if not re.match("^[\w\d-]*$", self.name):
            raise except_orm(
                _('Data error!'),
                _("Name can only contains letters, digits and underscore"))

    @api.one
    @api.constrains('application_id')
    def _check_backup(self):
        if not self.backup_ids and self.application_id.type_id.name \
                not in ['backup','backup_upload','archive','registry']:
            raise except_orm(
                _('Data error!'),
                _("You need to specify at least one backup container."))

    @api.one
    @api.constrains('image_id','image_version_id')
    def _check_config(self):
        if self.image_id.id != self.image_version_id.image_id.id:
            raise except_orm(_('Data error!'),
                _("The image of image version must be "
                  "the same than the image of container."))

    @api.one
    @api.constrains('option_ids')
    def _check_option_ids(self):
        for type_option in self.application_id.type_id.option_ids:
            if type_option.type == 'container' and type_option.required:
                test = False
                for option in self.option_ids:
                    if option.name == type_option and option.value:
                        test = True
                if not test:
                    raise except_orm(_('Data error!'),
                        _("You need to specify a value for the option " +
                          type_option.name + " for the container " +
                          self.name + "."))

    @api.one
    @api.constrains('link_ids')
    def _check_link_ids(self):
        for app_link in self.application_id.link_ids:
            if app_link.container and app_link.required:
                test = False
                for link in self.link_ids:
                    if link.name == app_link and link.target:
                        test = True
                if not test:
                    raise except_orm(_('Data error!'),
                        _("You need to specify a link to " +
                          app_link.name + " for the container " + self.name))

    @api.multi
    @api.onchange('application_id')
    def onchange_application_id(self):
        if self.application_id:
            self.server_id = self.application_id.next_server_id
            self.image_id = self.application_id.default_image_id
            self.privileged = self.application_id.default_image_id.privileged
            self.image_version_id = \
                self.application_id.default_image_id.version_ids \
                and self.application_id.default_image_id.version_ids[0]

            for type_option in self.application_id.type_id.option_ids:
                if type_option.type == 'container' and type_option.auto:
                    test = False
                    for option in self.option_ids:
                        if option.name == type_option:
                            test = True
                    if not test:
                        self.link_ids = [(0,0,{'name': type_option,
                                               'value': type_option.default})]

            for app_link in self.application_id.link_ids:
                if app_link.container and app_link.auto:
                    test = False
                    for link in self.link_ids:
                        if link.name == app_link:
                            test = True
                    if not test:
                        self.link_ids = [(0,0,{'name': app_link,
                                               'target': app_link.next})]

    # @api.multi
    # def get_vals(self):
    #     repo_obj = self.env['clouder.save.repository']
    #     vals = {}
    #
    #     now = datetime.now()
    #     if not self.save_repository_id:
    #         repo_ids = repo_obj.search([('container_name','=',self.name),('container_server','=',self.server_id.name)])
    #         if repo_ids:
    #             self.save_repository_id = repo_ids[0]
    #
    #     if not self.save_repository_id or datetime.strptime(self.save_repository_id.date_change, "%Y-%m-%d") < now or False:
    #         repo_vals ={
    #             'name': now.strftime("%Y-%m-%d") + '_' + self.name + '_' + self.server_id.name,
    #             'type': 'container',
    #             'date_change': (now + timedelta(days=self.saverepo_change or self.application_id.container_saverepo_change)).strftime("%Y-%m-%d"),
    #             'date_expiration': (now + timedelta(days=self.saverepo_expiration or self.application_id.container_saverepo_expiration)).strftime("%Y-%m-%d"),
    #             'container_name': self.name,
    #             'container_server': self.server_id.name,
    #         }
    #         repo_id = repo_obj.create(repo_vals)
    #         self.save_repository_id = repo_id
    #
    #     vals.update(self.image_version_id.get_vals())
    #     vals.update(self.application_id.get_vals())
    #     vals.update(self.save_repository_id.id.get_vals())
    #     vals.update(self.server_id.get_vals())
    #
    #     ports = {}
    #     ssh_port = 22
    #     for port in self.port_ids:
    #         ports[port.name] = {'id': port.id, 'name': port.name, 'localport': port.localport, 'hostport': port.hostport, 'expose': port.expose, 'udp': port.udp}
    #         if port.name == 'ssh':
    #             ssh_port = port.hostport
    #
    #     volumes = {}
    #     volumes_save = ''
    #     first = True
    #     for volume in self.volume_ids:
    #         volumes[volume.id] = {'id': volume.id, 'name': volume.name, 'hostpath': volume.hostpath, 'user': volume.user,'readonly': volume.readonly,'nosave': volume.nosave}
    #         if not volume.nosave:
    #             volumes_save += (not first and ',' or '') + volume.name
    #             first = False
    #
    #     options = {}
    #     for option in self.application_id.type_id.option_ids:
    #         if option.type == 'container':
    #             options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
    #     for option in self.option_ids:
    #         options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}
    #
    #     links = {}
    #     if 'app_links' in vals:
    #         for app_code, link in vals['app_links'].iteritems():
    #             if link['container'] or link['make_link']:
    #                 links[app_code] = link
    #                 links[app_code]['target'] = False
    #     for link in self.link_ids:
    #         if link.name.code in links and link.target:
    #             link_vals = link.get_vals()
    #             links[link.name.code]['target'] = {
    #                 'link_id': link_vals['container_id'],
    #                 'link_name': link_vals['container_name'],
    #                 'link_fullname': link_vals['container_fullname'],
    #                 'link_ssh_port': link_vals['container_ssh_port'],
    #                 'link_server_id': link_vals['server_id'],
    #                 'link_server_domain': link_vals['server_domain'],
    #                 'link_server_ip': link_vals['server_ip'],
    #             }
    #     for app_code, link in links.iteritems():
    #         if link['required'] and not link['target']:
    #             raise except_orm(_('Data error!'),
    #                 _("You need to specify a link to " + link['name'] + " for the container " + self.name))
    #         if not link['target']:
    #             del links[app_code]
    #
    #     backup_servers = []
    #     for backup in self.backup_server_ids:
    #         backup_vals = backup.get_vals()
    #         backup_servers.append({
    #             'container_id': backup_vals['container_id'],
    #             'container_fullname': backup_vals['container_fullname'],
    #             'server_id': backup_vals['server_id'],
    #             'server_ssh_port': backup_vals['server_ssh_port'],
    #             'server_domain': backup_vals['server_domain'],
    #             'server_ip': backup_vals['server_ip'],
    #             'backup_method': backup_vals['app_options']['backup_method']['value']
    #         })
    #
    #
    #     root_password = False
    #     for key, option in options.iteritems():
    #         if option['name'] == 'root_password':
    #             root_password = option['value']
    #
    #     fullname = self.name + '_' + vals['server_domain']
    #     vals.update({
    #         'container_id': self.id,
    #         'container_name': self.name,
    #         'container_fullname': fullname,
    #         'container_ports': ports,
    #         'container_volumes': volumes,
    #         'container_volumes_save': volumes_save,
    #         'container_ssh_port': ssh_port,
    #         'container_options': options,
    #         'container_links': links,
    #         'container_backup_servers': backup_servers,
    #         'container_no_save': self.nosave,
    #         'container_privileged': self.privileged,
    #         'container_shinken_configfile': '/usr/local/shinken/etc/services/' + fullname + '.cfg',
    #         'container_root_password': root_password
    #     })
    #
    #     return vals

    @api.multi
    def create_vals(self, vals):
        return vals

    @api.model
    def create(self, vals):
        if ('port_ids' not in vals or not vals['port_ids']) \
                and 'image_version_id' in vals:
            vals['port_ids'] = []
            for port in self.env['clouder.image.version'].\
                    browse(vals['image_version_id']).image_id.port_ids:
                if port.expose != 'none':
                    vals['port_ids'].append((0,0,{
                        'name':port.name,'localport':port.localport,
                        'expose':port.expose,'udp':port.udp}))
        if ('volume_ids' not in vals or not vals['volume_ids']) \
                and 'image_version_id' in vals:
            vals['volume_ids'] = []
            for volume in self.env['clouder.image.version']\
                    .browse(vals['image_version_id']).image_id.volume_ids:
                vals['volume_ids'].append((0,0,{
                    'name':volume.name, 'hostpath':volume.hostpath,
                    'user':volume.user, 'readonly':volume.readonly,
                    'nosave':volume.nosave}))
        if 'application_id' in vals:
            application = self.env['clouder.application']\
                .browse(vals['application_id'])
            self = self.with_context(apptype_name=application.type_id.name)

            if 'backup_ids' not in vals \
                    or not vals['backup_ids'] \
                    or not vals['backup_ids'][0][2]:
                vals['backup_ids'] = \
                    [(6,0,[b.id for b in application.container_backup_ids])]
            if 'time_between_save' not in vals \
                    or not vals['time_between_save']:
                vals['time_between_save'] = \
                    application.container_time_between_save
            if 'saverepo_change' not in vals or not vals['saverepo_change']:
                vals['saverepo_change'] = \
                    application.container_saverepo_change
            if 'saverepo_expiration' not in vals \
                    or not vals['saverepo_expiration']:
                vals['saverepo_expiration'] = \
                    application.container_saverepo_expiration
            if 'save_expiration' not in vals or not vals['save_expiration']:
                vals['save_expiration'] = \
                    application.container_save_expiration

#TODO a verifier si toujours utile apres la mise en place du onchange
            links = {}
            if 'link_ids' in vals:
                for link in vals['link_ids']:
                    link = link[2]
                    links[link['name']] = link
                del vals['link_ids']
            for application_link in application.link_ids:
                if (application_link.container or application_link.make_link) \
                        and application_link.id not in links:
                    links[application_link.id] = {}
                    links[application_link.id]['name'] = application_link.id
                    links[application_link.id]['target'] = False
            vals['link_ids'] = []
            for application_link_id, link in links.iteritems():
                if not link['target']:
                    application_link = self.env['clouder.application.link']\
                        .browse(application_link_id)
                    link['target'] = application_link.auto \
                                     and application_link.next or False
                vals['link_ids'].append((0,0,{'name': link['name'],
                                              'target': link['target']}))
        vals = self.create_vals(vals)
        return super(ClouderContainer, self).create(vals)

    @api.model
    def write(self, vals):
        version_obj = self.env['clouder.image.version']
        flag = False
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

    @api.model
    def unlink(self):
        self.service_ids and self.service_ids.unlink()
        self = self.with_context(save_comment='Before unlink')
        self.save()
        return super(ClouderContainer, self).unlink()

    # @api.multi
    # def button_stop(self):
    #     vals = self.get_vals()
    #     self.stop(vals)
    #
    # @api.multi
    # def button_start(self):
    #     vals = self.get_vals()
    #     self.start(vals)

    @api.multi
    def reinstall(self):
        if not 'save_comment' in self.env.context:
            self = self.with_context(save_comment='Before reinstall')
        self = self.with_context(forcesave=True)
        self.save()
        self = self.with_context(forcesave=False)
        self = self.with_context(nosave=True)
        super(ClouderContainer, self).reinstall()

    @api.multi
    def save(self):

        save = False
        now = datetime.now()
        repo_obj = self.env['clouder.save.repository']

        if not self.save_repository_id:
            repo_ids = repo_obj.search(
                [('container_name','=',self.name),
                 ('container_server','=',self.server_id.name)])
            if repo_ids:
                self.save_repository_id = repo_ids[0]

        if not self.save_repository_id \
                or datetime.strptime(self.save_repository_id.date_change,
                                     "%Y-%m-%d") < now or False:
            repo_vals ={
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
        self = self.with_context(self.create_log('save'))

        for backup_server in self.backup_ids:
            save_vals = {
                'name': self.now_bup() + '_' + self.container_fullname,
                'backup_id': backup_server.id,
                'repo_id': self.saverepo_id.id,
                'date_expiration': (now + timedelta(
                    days=self.save_expiration
                         or self.application_id.container_save_expiration
                )).strftime("%Y-%m-%d"),
                'comment': 'save_comment' in self.env.context
                           and self.env.context['save_comment']
                           or self.save_comment or 'Manual',
                'now_bup': self.now_bup(),
                'container_id': self.id,
            }
            save = self.env['clouder.save.save'].create(save_vals)
        next = (datetime.now() + timedelta(
            minutes=self.time_between_save
                    or self.application_id.container_time_between_save
        )).strftime("%Y-%m-%d %H:%M:%S")
        self.write({'save_comment': False, 'date_next_save': next})
        self.end_log()
        return save

    # @api.multi
    # def reset_key(self):
    #     vals = self.get_vals()
    #     self.deploy_key(vals)

    @api.multi
    def deploy_post(self):
        return

    @api.multi
    def deploy(self):

        self.purge()

        ssh = self.connect(self.server_id.name)

        cmd = ['sudo','docker', 'run', '-d']
        nextport = self.server_id.start_port
        for port in self.port_ids:
            if not port.hostport:
                while not port.hostport and nextport != self.server_id.end_port:
                    ports = self.env['clouder.container.port'].search(
                        [('hostport','=',nextport),
                         ('container_id.server_id','=',self.server_id.id)])
                    if not ports and not self.execute(ssh, [
                        'netstat', '-an', '|', 'grep', str(nextport)]):
                        port.hostport = nextport
                    nextport += 1
            udp = ''
            if port.udp:
                udp = '/udp'
            # cmd.extend(['-p', vals['server_ip'] + ':' + str(port['hostport']) + ':' + port['localport'] + udp])
            cmd.extend(['-p', str(port.hostport) + ':' + port.localport + udp])
        for volume in self.volume_ids:
            if volume.hostpath:
                arg = volume.hostpath + ':' + volume.name
                if volume.readonly:
                    arg += ':ro'
                cmd.extend(['-v', arg])
        for link in self.link_ids:
            if link.make_link and link.target.server_id== self.server_id:
                cmd.extend(['--link', link.target.name + ':' + link.name.code])
        if self.privileged:
            cmd.extend(['--privileged'])
        cmd.extend(['-v', '/opt/keys/' + self.fullname +
                    ':/opt/keys', '--name', self.name])

        if self.image_id.name == 'img_registry':
            cmd.extend([self.image_version_id.fullname])
        elif self.server_id == self.image_version_id.registry_id.server_id:
            cmd.extend([self.image_version_id.fullpath_localhost()])
        else:
            cmd.extend([self.image_version_id.fullpath()])

        #Deploy key now, otherwise the container will be angry to not find the key. We can't before because vals['container_ssh_port'] may not be set
        self.deploy_key()

        #Run container
        self.execute(ssh, cmd)

        time.sleep(3)

        self.deploy_post()

        self.start()

        ssh.close()

        for link in self.link_ids:
            if link.name.code == 'postfix':
                ssh = self.connect(self.fullname)
                self.execute(ssh, ['echo "root=' + self.email_sysadmin() +
                                   '" > /etc/ssmtp/ssmtp.conf'])
                self.execute(ssh, ['echo "mailhub=postfix:25" '
                                   '>> /etc/ssmtp/ssmtp.conf'])
                self.execute(ssh, ['echo "rewriteDomain=' + self.fullname +
                                   '" >> /etc/ssmtp/ssmtp.conf'])
                self.execute(ssh, ['echo "hostname=' + self.fullname +
                                   '" >> /etc/ssmtp/ssmtp.conf'])
                self.execute(ssh, ['echo "FromLineOverride=YES" >> '
                                   '/etc/ssmtp/ssmtp.conf'])
                ssh.close()

        #For shinken
        self.save()

        return

    @api.multi
    def purge(self):

        self.purge_key()

        ssh = self.connect(self.server_id.name)
        self.stop()
        self.execute(ssh, ['sudo','docker', 'rm', self.name])
        self.execute(ssh, ['rm', '-rf', '/opt/keys/' + self.fullname])
        ssh.close()

        return

    @api.multi
    def stop(self):
        ssh = self.connect(self.server_id.name)
        self.execute(ssh, ['docker', 'stop', self.name])
        ssh.close()

    @api.multi
    def start(self):
        self.stop()
        ssh = self.connect(self.server_id.name)
        self.execute(ssh, ['docker', 'start', self.name])
        ssh.close()
        time.sleep(3)

    @api.multi
    def deploy_key(self):
        # restart_required = False
        # try:
        #     ssh_container, sftp_container = execute.connect(vals['container_fullname'], context=context)
        # except:
        #     restart_required = True
        #     pass


        self.purge_key()
        self.execute_local(['ssh-keygen', '-t', 'rsa', '-C',
                            self.email_sysadmin, '-f', self.home_directory +
                            '/.ssh/keys/' + self.fullname, '-N', ''])
        self.execute_write_file(self.home_directory + '/.ssh/config',
                                'Host ' + self.fullname)
        self.execute_write_file(self.home_directory + '/.ssh/config',
                                '\n  HostName ' + self.server_id.name)
        self.execute_write_file(self.home_directory + '/.ssh/config',
                                '\n  Port ' + str(self.ssh_port))
        self.execute_write_file(self.home_directory + '/.ssh/config',
                                '\n  User root')
        self.execute_write_file(self.home_directory + '/.ssh/config',
                                '\n  IdentityFile ~/.ssh/keys/' + self.fullname)
        self.execute_write_file(self.home_directory + '/.ssh/config',
                                '\n#END ' + self.fullname + '\n')
        ssh = self.connect(self.server_id.name)
        self.execute(ssh, ['mkdir', '/opt/keys/' + self.fullname])
        self.send(ssh, self.home_directory + '/.ssh/keys/' +
                  self.fullname + '.pub', '/opt/keys/' +
                  self.fullname + '/authorized_keys')
        ssh.close()

        # _logger.info('restart required %s', restart_required)
        # if not restart_required:
        #     execute.execute(ssh_container, ['supervisorctl', 'restart', 'sshd'], context)
        #     ssh_container.close()
        #     sftp_container.close()
        # else:
        #     self.start(cr, uid, vals, context=context)


        if self.application_id.type_id.name == 'backup':
            shinkens = self.search(
                [('application_id.type_id.name', '=','shinken')])
            if not shinkens:
                self.log('The shinken isnt configured in conf, '
                         'skipping deploying backup keys in shinken')
                return
            for shinken in shinkens:
                ssh = self.connect(
                    shinken.fullname, username='shinken')
                self.execute(ssh, ['rm', '-rf', '/home/shinken/.ssh/keys/' +
                                   self.fullname + '*'])
                self.send(
                    sftp, self.home_directory + '/.ssh/keys/' +
                    self.fullname + '.pub', '/home/shinken/.ssh/keys/' +
                    self.fullname + '.pub')
                self.send(ssh, self.home_directory + '/.ssh/keys/' +
                          self.fullname, '/home/shinken/.ssh/keys/' +
                          self.fullname)
                self.execute(ssh, ['chmod', '-R', '700', '/home/shinken/.ssh'])
                self.execute(ssh, [
                    'sed', '-i', "'/Host " + self.fullname +
                    "/,/END " + self.fullname + "/d'",
                    '/home/shinken/.ssh/config'])
                self.execute(ssh, [
                    'echo "Host ' + self.fullname +
                    '" >> /home/shinken/.ssh/config'])
                self.execute(ssh, [
                    'echo "    Hostname ' +
                    self.server_id.name + '" >> /home/shinken/.ssh/config'])
                self.execute(ssh, [
                    'echo "    Port ' + str(self.ssh_port) +
                    '" >> /home/shinken/.ssh/config'])
                self.execute(ssh, [
                    'echo "    User backup" >> /home/shinken/.ssh/config'])
                self.execute(ssh, [
                    'echo "    IdentityFile  ~/.ssh/keys/' +
                    self.fullname + '" >> /home/shinken/.ssh/config'])
                self.execute(ssh, ['echo "#END ' + self.fullname +
                                   '" >> ~/.ssh/config'])

    @api.multi
    def purge_key(self):
        self.execute_local([
            modules.get_module_path('clouder') + '/res/sed.sh',
            self.fullname, self.home_directory + '/.ssh/config'])
        self.execute_local([
            'rm', '-rf', self.home_directory +
            '/.ssh/keys/' + self.fullname])
        self.execute_local([
            'rm', '-rf', self.home_directory +
            '/.ssh/keys/' + self.fullname + '.pub'])
        ssh = self.connect(self.server_id.name)
        self.execute(ssh, [
            'rm', '-rf', '/opt/keys/' + self.fullname + '/authorized_keys'])
        ssh.close()


class ClouderContainerPort(models.Model):
    _name = 'clouder.container.port'

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Char('Name', size=64, required=True)
    localport = fields.Char('Local port', size=12, required=True)
    hostport = fields.Char('Host port', size=12)
    expose = fields.Selection(
        [('internet','Internet'),('local','Local')],'Expose?',
        required=True, default='local')
    udp = fields.Boolean('UDP?')

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)',
         'Port name must be unique per container!'),
    ]


class ClouderContainerVolume(models.Model):
    _name = 'clouder.container.volume'

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
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
        if not self.name.required and not self.value:
            raise except_orm(
                _('Data error!'),
                _("You need to specify a value for the option " +
                  self.name.name + " for the container " +
                  self.container_id.name + "."))


class ClouderContainerLink(models.Model):
    _name = 'clouder.container.link'

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Many2one(
        'clouder.application.link', 'Application Link', required=True)
    target = fields.Many2one('clouder.container', 'Target')

    @api.one
    @api.constrains('container_id')
    def _check_required(self):
        if not self.name.required and not self.target:
            raise except_orm(
                _('Data error!'),
                _("You need to specify a link to " +
                  self.name.application_id.name + " for the container " +
                  self.container_id.name))


    # @api.multi
    # def get_vals(self):
    #     vals = {}
    #
    #     vals.update(self.container_id.get_vals())
    #     if self.target:
    #         target_vals = self.target_id.get_vals()
    #         vals.update({
    #             'link_target_container_id': target_vals['container_id'],
    #             'link_target_container_name': target_vals['container_name'],
    #             'link_target_container_fullname': target_vals['container_fullname'],
    #             'link_target_app_id': target_vals['app_id'],
    #             'link_target_app_code': target_vals['app_code'],
    #         })
    #
    #
    #     return vals

    # @api.multi
    # def reload(self):
    #     vals = self.get_vals()
    #     self.deploy(vals)
    #     return

    @api.multi
    def deploy_link(self):
        return

    @api.multi
    def purge_link(self):
        return

    @api.multi
    def control(self):
        if not self.target:
            self.log('The target isnt configured in the link, '
                     'skipping deploy link')
            return False
        app_links = self.search(
            [('container_id','=',self.container_id.id),
             ('name.code','=', self.target.application_id.code)])
        if not app_links:
            self.log('The target isnt in the application link for container, '
                     'skipping deploy link')
            return False
        if not app_links[0].container:
            self.log('This application isnt for container, '
                     'skipping deploy link')
            return False
        return True

    @api.multi
    def deploy(self):
        self.purge()
        self.control() and self.deploy_link()

    @api.multi
    def purge(self):
        self.control() and self.purge_link()

