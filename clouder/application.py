# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Buron
#    Copyright 2015 Yannick Buron
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
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)


class ClouderApplicationType(models.Model):
    _name = 'clouder.application.type'

    name = fields.Char('Name', size=64, required=True)
    system_user = fields.Char('System User', size=64, required=True)
    localpath = fields.Char('Localpath', size=128)
    localpath_services = fields.Char('Localpath Services', size=128)
    option_ids = fields.One2many('clouder.application.type.option', 'apptype_id', 'Options')
    application_ids = fields.One2many('clouder.application', 'type_id', 'Applications')
    symlink = fields.Boolean('Use Symlink by default?')
    multiple_databases = fields.Char('Multiples databases?', size=128)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    # @api.multi
    # def get_vals(self):
    #
    #     vals = {}
    #
    #     vals.update(self.env.ref('clouder.clouder_settings').get_vals())
    #
    #     options = {
    #         'application': {},
    #         'container': {},
    #         'service': {},
    #         'base': {}
    #     }
    #     for option in self.option_ids:
    #         options[option.type][option.name] = {'id': option.id, 'name': option.name, 'type': option.type, 'default': option.default}
    #
    #     vals.update({
    #         'apptype_name': self.name,
    #         'apptype_system_user': self.system_user,
    #         'apptype_localpath': self.localpath,
    #         'apptype_localpath_services': self.localpath_services,
    #         'apptype_options': options,
    #         'apptype_symlink': self.symlink,
    #         'apptype_multiple_databases': self.multiple_databases,
    #     })
    #
    #     return vals


class ClouderApplicationTypeOption(models.Model):
    _name = 'clouder.application.type.option'

    apptype_id = fields.Many2one('clouder.application.type', 'Application Type', ondelete="cascade", required=True)
    name = fields.Char('Name', size=64, required=True)
    type = fields.Selection([('application','Application'),('container','Container'),('service','Service'),('base','Base')], 'Type', required=True)
    default = fields.Text('Default value')

    _sql_constraints = [
        ('name_uniq', 'unique(apptype_id,name)', 'Options name must be unique per apptype!'),
    ]


class ClouderApplication(models.Model):
    _name = 'clouder.application'

    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', size=10, required=True)
    type_id = fields.Many2one('clouder.application.type', 'Type', required=True)
    current_version = fields.Char('Current version', size=64, required=True)
    next_server_id = fields.Many2one('clouder.server', 'Next server')
    default_image_id = fields.Many2one('clouder.image', 'Default Image', required=True)
    admin_name = fields.Char('Admin name', size=64)
    admin_email = fields.Char('Admin email', size=64)
    archive_id = fields.Many2one('clouder.container', 'Archive')
    option_ids = fields.One2many('clouder.application.option', 'application_id', 'Options')
    link_ids = fields.One2many('clouder.application.link', 'application_id', 'Links')
    version_ids = fields.One2many('clouder.application.version', 'application_id', 'Versions')
    buildfile = fields.Text('Build File')
    container_ids = fields.One2many('clouder.container', 'application_id', 'Containers')
    container_backup_ids = fields.Many2many('clouder.container', 'clouder_application_container_backup_rel', 'application_id', 'backup_id', 'Backups Containers')
    container_time_between_save = fields.Integer('Minutes between each container save', required=True)
    container_saverepo_change = fields.Integer('Days before container saverepo change', required=True)
    container_saverepo_expiration = fields.Integer('Days before container saverepo expiration', required=True)
    container_save_expiration = fields.Integer('Days before container save expiration', required=True)
    base_backup_ids = fields.Many2many('clouder.container', 'clouder_application_base_backup_rel', 'application_id', 'backup_id', 'Backups Bases')
    base_time_between_save = fields.Integer('Minutes between each base save', required=True)
    base_saverepo_change = fields.Integer('Days before base saverepo change', required=True)
    base_saverepo_expiration = fields.Integer('Days before base saverepo expiration', required=True)
    base_save_expiration = fields.Integer('Days before base save expiration', required=True)

    full_archivepath = lambda self : self.env.ref('clouder.clouder_settings').archive_path() + '/' + self.type_id.name + '-' + self.code
    full_hostpath = lambda  self : self.env.ref('clouder.clouder_settings').services_hostpath() + '/' + self.type_id.name + '-' + self.code
    full_localpath = lambda self: self.type_id.localpath and self.type_id.localpath() + '/' + self.type_id.name + '-' + self.code or ''
    computed_version = lambda self: self.current_version + '.' + datetime.now().strftime('%Y%m%d.%H%M%S')

    def options(self):
        options = {}
        for option in self.type_id.option_ids:
            if option.type == 'application':
                options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
        for option in self.option_ids:
            options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}
        return options

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Code must be unique!'),
    ]

    # @api.multi
    # def get_vals(self):
    #
    #     vals = {}
    #
    #     vals.update(self.type_id.get_vals())
    #
    #     now = datetime.now()
    #     computed_version = self.current_version + '.' + now.strftime('%Y%m%d.%H%M%S')
    #
    #     options = {}
    #     for option in self.type_id.option_ids:
    #         if option.type == 'application':
    #             options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
    #     for option in self.option_ids:
    #         options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}
    #
    #     links = {}
    #     for link in self.link_ids:
    #         links[link.name.code] = {
    #             'id': link.id, 'app_id': link.name.id, 'name': link.name.name, 'code': link.name.code,
    #             'required': link.required, 'auto': link.auto, 'make_link': link.make_link, 'next': link.next,
    #             'container': link.container, 'service': link.service, 'base': link.base
    #         }
    #
    #
    #     vals.update({
    #         'app_id': self.id,
    #         'app_name': self.name,
    #         'app_code': self.code,
    #         'app_full_archivepath': vals['config_archive_path'] + '/' + self.type_id.name + '-' + self.code,
    #         'app_full_hostpath': vals['config_services_hostpath'] + self.type_id.name + '-' + self.code,
    #         'app_full_localpath': vals['apptype_localpath'] and vals['apptype_localpath'] + '/' + self.type_id.name + '-' + self.code or '',
    #         'app_admin_name': self.admin_name,
    #         'app_admin_email': self.admin_email,
    #         'app_current_version': self.current_version,
    #         'app_computed_version': computed_version,
    #         'app_buildfile': self.buildfile,
    #         'app_options': options,
    #         'app_links': links
    #     })
    #
    #     return vals

    @api.multi
    def get_current_version(self):
        return False

    @api.multi
    def build(self):

        if not self.archive_id:
            raise except_orm(_('Data error!'),_("You need to specify the archive where the version must be stored."))

        current_version = self.get_current_version()
        if current_version:
            self.write({'current_version': current_version})
        current_version = current_version or self.current_version
        now = datetime.now()
        version = current_version + '.' + now.strftime('%Y%m%d.%H%M')
        self.env['clouder.application.version'].create({'application_id': self.id, 'name': version, 'archive_id': self.archive_id and self.archive_id.id})


class ClouderApplicationOption(models.Model):
    _name = 'clouder.application.option'

    application_id = fields.Many2one('clouder.application', 'Application', ondelete="cascade", required=True)
    name = fields.Many2one('clouder.application.type.option', 'Option', required=True)
    value = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(application_id,name)', 'Option name must be unique per application!'),
    ]


class ClouderApplicationVersion(models.Model):
    _name = 'clouder.application.version'
    _inherit = ['clouder.model']

    name = fields.Char('Name', size=64, required=True)
    application_id = fields.Many2one('clouder.application', 'Application', required=True)
    archive_id = fields.Many2one('clouder.container', 'Archive', required=True)
    service_ids = fields.One2many('clouder.service','application_version_id', 'Services')

    fullname = lambda self: self.application_id.code + '_' + self.name
    full_archivepath = lambda self : self.application_id.full_archivepath() + '/' + self.name
    full_archivepath_targz = lambda self : self.application_id.full_archivepath() + '/' + self.name + '.tar.gz'
    full_hostpath = lambda self : self.application_id.full_hostpath() + '/' + self.name
    full_localpath = lambda self : self.application_id.full_localpath() + '/' + self.name

    _sql_constraints = [
        ('name_app_uniq', 'unique (name,application_id)', 'The name of the version must be unique per application !')
    ]

    _order = 'create_date desc'

    # @api.multi
    # def get_vals(self):
    #
    #     vals = {}
    #
    #     vals.update(self.application_id.get_vals())
    #
    #
    #     archive_vals = self.archive_id.get_vals()
    #     vals.update({
    #         'archive_id': archive_vals['container_id'],
    #         'archive_fullname': archive_vals['container_fullname'],
    #         'archive_server_id': archive_vals['server_id'],
    #         'archive_server_ssh_port': archive_vals['server_ssh_port'],
    #         'archive_server_domain': archive_vals['server_domain'],
    #         'archive_server_ip': archive_vals['server_ip'],
    #     })
    #
    #     vals.update({
    #         'app_version_id': self.id,
    #         'app_version_name': self.name,
    #         'app_version_fullname': vals['app_code'] + '_' + self.name,
    #         'app_version_full_archivepath': vals['app_full_archivepath'] + '/' + self.name,
    #         'app_version_full_archivepath_targz': vals['app_full_archivepath'] + '/' + self.name + '.tar.gz',
    #         'app_version_full_hostpath': vals['app_full_hostpath'] + '/' + self.name,
    #         'app_version_full_localpath': vals['app_full_localpath'] + '/' + self.name,
    #     })
    #
    #     return vals

    @api.multi
    def unlink(self):
        if self.service_ids:
            raise except_orm(_('Inherit error!'),_("A service is linked to this application version, you can't delete it!"))
        return super(ClouderApplicationVersion, self).unlink()


    @api.multi
    def build_application(self):
        return

    @api.multi
    def deploy(self):
        ssh, sftp = self.connect(self.archive_id.fullname())
        self.execute(ssh, ['mkdir', self.application_id.full_archivepath()])
        self.execute(ssh, ['rm', '-rf', self.full_archivepath()])
        self.execute(ssh, ['mkdir', self.full_archivepath()])
        self.build_application()
        self.execute(ssh, ['echo "' + self.name + '" >> ' +  self.full_archivepath() + '/VERSION.txt'])
        self.execute(ssh, ['tar', 'czf', self.full_archivepath_targz(), '-C', self.application_id.full_archivepath() + '/' + self.name, '.'])
        ssh.close(), sftp.close()

    @api.multi
    def purge(self):
        ssh, sftp = self.connect(self.archive_id.fullname())
        self.execute(ssh, ['rm', '-rf', self.full_archivepath()])
        self.execute(ssh, ['rm', self.full_archivepath_targz()])
        ssh.close(), sftp.close()


class ClouderApplicationLink(models.Model):
    _name = 'clouder.application.link'

    application_id = fields.Many2one('clouder.application', 'Application', ondelete="cascade", required=True)
    name = fields.Many2one('clouder.application', 'Application', required=True)
    required = fields.Boolean('Required?')
    auto = fields.Boolean('Auto?')
    make_link = fields.Boolean('Make docker link?')
    container = fields.Boolean('Container?')
    service = fields.Boolean('Service?')
    base = fields.Boolean('Base?')
    next = fields.Many2one('clouder.container', 'Next')

    def get_dict(self):
        return {
            'id': self.id, 'app_id': self.name.id, 'name': self.name.name, 'code': self.name.code,
            'required': self.required, 'auto': self.auto, 'make_link': self.make_link, 'next': self.next,
            'container': self.container, 'service': self.service, 'base': self.base
        }

    _sql_constraints = [
        ('name_uniq', 'unique(application_id,name)', 'Links must be unique per application!'),
    ]