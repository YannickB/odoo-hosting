# -*- coding: utf-8 -*-
# #############################################################################
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
import re

import clouder_model

import logging

_logger = logging.getLogger(__name__)


class ClouderService(models.Model):
    _name = 'clouder.service'
    _inherit = ['clouder.model']

    @api.multi
    def name_get(self):
        return (self.id, self.name + ' [' + self.container_id.name +
                '_' + self.container_id.server_id.name + ']')

    @api.multi
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            ids = self.search(
                ['|', ('name', 'like', name),
                 '|', ('container_id.name', 'like', name),
                 ('container_id.server_id.name', 'like', name)] + args,
                limit=limit)
        else:
            ids = self.search(args, limit=limit)
        result = ids.name_get()
        return result


    name = fields.Char('Name', size=64, required=True)
    application_id = fields.Many2one(
        'clouder.application', 'Application',
        relation='container_id.application_id', readonly=True)
    application_version_id = fields.Many2one(
        'clouder.application.version', 'Version',
        domain="[('application_id.container_ids','in',container_id)]",
        required=True)
    database_password = fields.Char(
        'Database password', size=64, required=True,
        default=clouder_model.generate_random_password(20))
    container_id = fields.Many2one(
        'clouder.container', 'Container', required=True)
    skip_analytics = fields.Boolean('Skip Analytics?')
    option_ids = fields.One2many(
        'clouder.service.option', 'service_id', 'Options')
    link_ids = fields.One2many(
        'clouder.service.link', 'service_id', 'Links')
    base_ids = fields.One2many('clouder.base', 'service_id', 'Bases')
    parent_id = fields.Many2one('clouder.service', 'Parent Service')
    sub_service_name = fields.Char('Subservice Name', size=64)
    custom_version = fields.Boolean('Custom Version?')
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.user_partner)
    partner_ids = fields.Many2many(
        'res.partner', 'clouder_service_partner_rel',
        'service_id', 'partner_id', 'Users')

    @property
    def fullname(self):
        return self.container_id.name + '-' + self.name

    @property
    def full_localpath(self):
        return self.application_id.type_id.localpath_services + '/' + self.name

    @property
    def full_localpath_files(self):
        return self.application_id.type_id.localpath_services + \
               '/' + self.name + '/files'

    @property
    def database(self):
        database = False
        for link in self.link_ids:
            if link.target:
                if link.name.application_id.code in ['postgres', 'mysql']:
                    database = link.target
        return database

    @property
    def database_type(self):
        return self.database().application_id.type_id.name

    @property
    def database_server(self):
        if self.database().server_id == self.container_id.server_id:
            return self.database().name
        else:
            return self.database().server_id.name

    @property
    def db_user(self):
        db_user = self.fullname.replace('-', '_')
        if self.database_type() == 'mysql':
            db_user = self.container_id.name[:10] + '_' + self.name[:4]
            db_user = db_user.replace('-', '_')
        return db_user

    @property
    def options(self):
        options = {}
        for option in self.container_id.application_id.type_id.option_ids:
            if option.type == 'service':
                options[option.name] = {
                    'id': option.id, 'name': option.name,
                    'value': option.default}
        for option in self.option_ids:
            options[option.name.name] = {
                'id': option.id, 'name': option.name.name,
                'value': option.value}

        if 'port' in options:
            test = False
            for port in self.port_ids:
                if options['port']['value'] == port.localport:
                    options['port']['localport'] = port.localport
                    options['port']['hostport'] = port.hostport
        return options

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)',
         'Name must be unique per container!'),
    ]

    @api.one
    @api.constrains('name', 'sub_service_name')
    def _validate_data(self):
        if not re.match("^[\w\d_]*$", self.name):
            raise except_orm(
                _('Data error!'),
                _("Name can only contains letters, digits and underscore "))
        if self.sub_service_name \
                and not re.match("^[\w\d_]*$", self.sub_service_name):
            raise except_orm(
                _('Data error!'),
                _("Sub service name can only contains letters, "
                  "digits and underscore "))

    @api.one
    @api.constrains('container_id')
    def _check_application(self):
        if self.application_id.id != self.container_id.application_id.id:
            raise except_orm(
                _('Data error!'),
                _("The application of service must be the same "
                  "than the application of container."))

    @api.one
    @api.constrains('application_id', 'application_version_id')
    def _check_application_version(self):
        if self.application_id.id != \
                self.application_version_id.application_id.id:
            raise except_orm(
                _('Data error!'),
                _("The application of application version must "
                  "be the same than the application of service."))

    @api.one
    @api.constrains('link_ids')
    def _check_database(self):
        if not self.database():
            raise except_orm(
                _('Data error!'),
                _("You need to specify a database in the links "
                  "of the service " + self.name + " " +
                  self.container_id.fullname))

    @api.one
    @api.constrains('option_ids')
    def _check_option_ids(self):
        for type_option in self.application_id.type_id.option_ids:
            if type_option.type == 'service' and type_option.required:
                test = False
                for option in self.option_ids:
                    if option.name == type_option and option.value:
                        test = True
                if not test:
                    raise except_orm(
                        _('Data error!'),
                        _("You need to specify a value for the option " +
                          type_option.name + " for the service " +
                          self.name + "."))

    @api.one
    @api.constrains('link_ids')
    def _check_link_ids(self):
        for app_link in self.application_id.link_ids:
            if app_link.service and app_link.required:
                test = False
                for link in self.link_ids:
                    if link.name == app_link and link.target:
                        test = True
                if not test:
                    raise except_orm(
                        _('Data error!'),
                        _("You need to specify a link to " +
                          app_link.name + " for the service " + self.name))


    @api.multi
    @api.onchange('application_id')
    def onchange_application_id(self):
        if self.application_id:

            options = []
            for type_option in self.application_id.type_id.option_ids:
                if type_option.type == 'service' and type_option.auto:
                    test = False
                    for option in self.option_ids:
                        if option.name == type_option:
                            test = True
                    if not test:
                        options.append((0, 0, {'name': type_option,
                                               'value': type_option.default}))
            self.option_ids = options

            links = []
            for app_link in self.application_id.link_ids:
                if app_link.service and app_link.auto:
                    test = False
                    for link in self.link_ids:
                        if link.name == app_link:
                            test = True
                    if not test:
                        links.append((0, 0, {'name': app_link,
                                             'target': app_link.next}))
            self.link_ids = links


    # @api.multi
    # def get_vals(self):
    #
    #     vals = {}
    #
    #     vals.update(self.application_version_id.get_vals())
    #
    #     vals.update(self.container_id.get_vals())
    #
    #     options = {}
    #     for option in self.container_id.application_id.type_id.option_ids:
    #         if option.type == 'service':
    #             options[option.name] = {'id': option.id, 'name': option.name, 'value': option.default}
    #     for option in self.option_ids:
    #         options[option.name.name] = {'id': option.id, 'name': option.name.name, 'value': option.value}
    #
    #     links = {}
    #     if 'app_links' in vals:
    #         for app_code, link in vals['app_links'].iteritems():
    #             if link['service']:
    #                 links[app_code] = link
    #                 links[app_code]['target'] = False
    #     for link in self.link_ids:
    #         if link.name.code in links and link.target:
    #             link_vals = link.target.get_vals()
    #             links[link.name.code]['target'] = {
    #                 'link_id': link_vals['container_id'],
    #                 'link_name': link_vals['container_name'],
    #                 'link_fullname': link_vals['container_fullname'],
    #                 'link_ssh_port': link_vals['container_ssh_port'],
    #                 'link_server_id': link_vals['server_id'],
    #                 'link_server_domain': link_vals['server_domain'],
    #                 'link_server_ip': link_vals['server_ip'],
    #             }
    #             database = False
    #             if link.name.code == 'postgres':
    #                 vals['database_type'] = 'pgsql'
    #                 database = 'postgres'
    #             elif link.name.code == 'mysql':
    #                 vals['database_type'] = 'mysql'
    #                 database = 'mysql'
    #             if database:
    #                 vals.update({
    #                     'database_id': link_vals['container_id'],
    #                     'database_fullname': link_vals['container_fullname'],
    #                     'database_ssh_port': link_vals['container_ssh_port'],
    #                     'database_server_id': link_vals['server_id'],
    #                     'database_server_domain': link_vals['server_domain'],
    #                     'database_root_password': link_vals['container_root_password'],
    #                 })
    #                 if links[link.name.code]['make_link'] and vals['database_server_id'] == vals['server_id']:
    #                     vals['database_server'] = database
    #                 else:
    #                     vals['database_server'] = vals['database_server_domain']
    #     for app_code, link in links.iteritems():
    #         if link['required'] and not link['target']:
    #             raise except_orm(_('Data error!'),
    #                 _("You need to specify a link to " + link['name'] + " for the service " + self.name))
    #         if not link['target']:
    #             del links[app_code]
    #
    #     service_fullname = vals['container_name'] + '-' + self.name
    #     db_user = service_fullname.replace('-','_')
    #     if not 'database_type' in vals:
    #         raise except_orm(_('Data error!'),
    #             _("You need to specify a database in the links of the service " + self.name + " " + vals['container_fullname']))
    #     if vals['database_type'] == 'mysql':
    #         db_user = vals['container_name'][:10] + '_' + self.name[:4]
    #         db_user = db_user.replace('-','_')
    #     vals.update({
    #         'service_id': self.id,
    #         'service_name': self.name,
    #         'service_fullname': service_fullname,
    #         'service_db_user': db_user,
    #         'service_db_password': self.database_password,
    #         'service_skip_analytics': self.skip_analytics,
    #         'service_full_localpath': vals['apptype_localpath_services'] + '/' + self.name,
    #         'service_full_localpath_files': vals['apptype_localpath_services'] + '/' + self.name + '/files',
    #         'service_options': options,
    #         'service_links': links,
    #         'service_subservice_name': self.sub_service_name,
    #         'service_custom_version': self.custom_version
    #     })
    #
    #     return vals

    @api.multi
    def write(self, vals):
        res = super(ClouderService, self).write(vals)
        if 'application_version_id' in vals:
            self.check_files()
        if 'application_version_id' in vals or 'custom_version' in vals:
            self.deploy_files()
        return res

    @api.one
    def unlink(self):
        self.base_ids and self.base_ids.unlink()
        return super(ClouderService, self).unlink()

    @api.multi
    def install_formation(self):
        self.sub_service_name = 'formation'
        self.install_subservice()

    @api.multi
    def install_test(self):
        self.sub_service_name = 'test'
        self.install_subservice()

    @api.multi
    def install_subservice(self):
        if not self.sub_service_name or self.sub_service_name == self.name:
            return
        services = self.search([('name', '=', self.sub_service_name),
                                ('container_id', '=', self.container_id.id)])
        services.unlink()
        options = []
        type_ids = self.env['clouder.application.type.option'].search(
            [('apptype_id', '=', self.container_id.application_id.type_id.id),
             ('name', '=', 'port')])
        if type_ids:
            if self.sub_service_name == 'formation':
                options = [(0, 0, {'name': type_ids[0],
                                   'value': 'port-formation'})]
            if self.sub_service_name == 'test':
                options = [(0, 0, {'name': type_ids[0],
                                   'value': 'port-test'})]
        links = []
        for link in self.link_ids:
            links.append((0, 0, {
                'name': link.name.id,
                'target': link.target and link.target.id or False
            }))
        service_vals = {
            'name': self.sub_service_name,
            'container_id': self.container_id.id,
            'application_version_id': self.application_version_id.id,
            'parent_id': self.id,
            'option_ids': options,
            'link_ids': links
        }
        subservice = self.create(service_vals)
        for base in self.base_ids:
            subbase_name = self.sub_service_name + '-' + base.name
            self = self.with_context(
                save_comment='Duplicate base into ' + subbase_name)
            base._reset_base(subbase_name, service_id=subservice)
        self.sub_service_name = False

    @api.multi
    def deploy_to_parent(self):
        if not self.parent_id:
            return
        vals = {}
        if not self.parent_id.custom_version:
            vals['application_version_id'] = self.application_version_id.id
        else:
            self = self.with_context(files_from_service=self.name)
            vals['custom_version'] = True
        self.parent_id.write(vals)

    @api.multi
    def deploy_post_service(self):
        return

    @api.multi
    def deploy(self):
        container_obj = self.env['clouder.container']

        self.purge()

        self.log('Creating database user')

        #SI postgres, create user
        if self.database_type() != 'mysql':
            ssh = self.connect(
                self.database().fullname, username='postgres')
            self.execute(ssh, [
                'psql', '-c', '"CREATE USER ' + self.db_user() +
                ' WITH PASSWORD \'' + self.database_password + '\' CREATEDB;"'
            ])
            ssh.close()

            ssh = self.connect(
                self.container_id.fullname,
                username=self.application_id.type_id.system_user)
            self.execute(ssh, [
                'sed', '-i', '"/:*:' + self.db_user() + ':/d" ~/.pgpass'])
            self.execute(ssh, [
                'echo "' + self.database_server() + ':5432:*:' +
                self.db_user() + ':' + self.database_password +
                '" >> ~/.pgpass'])
            self.execute(ssh, ['chmod', '700', '~/.pgpass'])
            ssh.close()

        else:
            ssh = self.connect(self.database().fullname)
            self.execute(ssh, [
                "mysql -u root -p'" + self.database().root_password() +
                "' -se \"create user '" + self.db_user() +
                "' identified by '" + self.database_password + "';\""])
            ssh.close()

        self.log('Database user created')

        ssh = self.connect(
            self.container_id.fullname,
            username=self.application_id.type_id.system_user)
        self.execute(ssh, ['mkdir', '-p', self.full_localpath])
        ssh.close()

        self.deploy_files()
        self.deploy_post_service()

        container_obj.start()

        # ssh = connect(vals['server_domain'], vals['apptype_system_user'], context=context)
        # if sftp.stat(vals['service_fullpath']):
        # log('Service ok', context=context)
        # else:
        # log('There was an error while creating the instance', context=context)
        # context['log_state'] == 'ko'
        # ko_log(context=context)
        # ssh.close()

    @api.multi
    def purge_pre_service(self):
        return

    @api.multi
    def purge(self):
        self.purge_files()
        self.purge_pre_service()

        ssh = self.connect(
            self.container_id.fullname,
            username=self.application_id.type_id.system_user)
        self.execute(ssh, ['rm', '-rf', self.full_localpath])
        ssh.close()

        if self.database_type() != 'mysql':
            ssh = self.connect(
                self.database().fullname, username='postgres')
            self.execute(ssh, [
                'psql', '-c', '"DROP USER ' + self.db_user() + ';"'])
            ssh.close()

            ssh = self.connect(
                self.container_id.fullname,
                username=self.application_id.type_id.system_user)
            self.execute(ssh, [
                'sed', '-i', '"/:*:' + self.db_user() + ':/d" ~/.pgpass'])
            ssh.close()

        else:
            ssh = self.connect(self.database().fullname)
            self.execute(ssh, [
                "mysql -u root -p'" + self.database().root_password +
                "' -se \"drop user " + self.db_user() + ";\""])
            ssh.close()

        return

    @api.multi
    def check_files(self):
        services = self.search([
            ('application_version_id', '=', self.application_version_id.id),
            ('container_id.server_id', '=', self.container_id.server_id.id)])
        if self in services:
            services.remove(self)
        if not services:
            ssh = self.connect(self.container_id.server_id.name)
            self.execute(ssh, [
                'rm', '-rf', self.application_version_id.full_hostpath])
            ssh.close()

    @api.multi
    def deploy_files(self):
        base_obj = self.env['clouder.base']
        self.purge_files()
        ssh = self.connect(self.container_id.server_id.name)

        if not self.exist(sftp, self.application_version_id.full_hostpath):
            ssh_archive, sftp_archive = self.connect(
                self.application_version_id.archive_id.fullname)
            tmp = '/tmp/' + self.application_version_id.fullname + '.tar.gz'
            self.log(
                'sftp get ' +
                self.application_version_id.full_archivepath_targz + ' ' + tmp)
            sftp_archive.get(
                self.application_version_id.full_archivepath_targz, tmp)
            ssh_archive.close(), sftp_archive.close()
            self.execute(ssh, [
                'mkdir', '-p', self.application_version_id.full_hostpath])
            self.log('sftp put ' + tmp + ' ' +
                     self.application_version_id.full_hostpath + '.tar.gz')
            self.send(ssh, tmp,
                      self.application_version_id.full_hostpath + '.tar.gz')
            self.execute(ssh, [
                'tar', '-xf',
                self.application_version_id.full_hostpath + '.tar.gz',
                '-C', self.application_version_id.full_hostpath])
            self.execute(ssh, [
                'rm', self.application_id.full_hostpath + '/' +
                self.application_version_id.name + '.tar.gz'])

        ssh.close()

        ssh = self.connect(
            self.container_id.fullname,
            username=self.application_id.type_id.system_user)
        if 'files_from_service' in self.env.context:
            self.execute(ssh, [
                'cp', '-R', self.application_id.type_id.localpath_services +
                '/' + self.env.context['files_from_service'] + '/files',
                self.full_localpath_files])
        elif self.custom_version or not self.application_id.type_id.symlink:
            self.execute(ssh, [
                'cp', '-R', self.application_version_id.full_localpath,
                self.full_localpath_files])
        else:
            self.execute(ssh, [
                'ln', '-s', self.application_version_id.full_localpath,
                self.full_localpath_files])

        for base in self.base_ids:
            base.save()
            base.update_base()
        ssh.close()

    @api.multi
    def purge_files(self):
        ssh = self.connect(
            self.container_id.fullname,
            username=self.application_id.type_id.system_user)
        self.execute(ssh, ['rm', '-rf', self.full_localpath_files])
        ssh.close()
        self.check_files()


class ClouderServiceOption(models.Model):
    _name = 'clouder.service.option'

    service_id = fields.Many2one(
        'clouder.service', 'Service', ondelete="cascade", required=True)
    name = fields.Many2one(
        'clouder.application.type.option', 'Option', required=True)
    value = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(service_id,name)',
         'Option name must be unique per service!'),
    ]

    @api.one
    @api.constrains('service_id')
    def _check_required(self):
        if self.name.required and not self.value:
            raise except_orm(
                _('Data error!'),
                _("You need to specify a value for the option " +
                  self.name.name + " for the service " +
                  self.service_id.name + "."))


class ClouderServiceLink(models.Model):
    _name = 'clouder.service.link'
    _inherit = ['clouder.model']

    service_id = fields.Many2one(
        'clouder.service', 'Service', ondelete="cascade", required=True)
    name = fields.Many2one(
        'clouder.application.link', 'Application Link', required=True)
    target = fields.Many2one(
        'clouder.container', 'Target')

    @api.one
    @api.constrains('service_id')
    def _check_required(self):
        if self.name.required and not self.target:
            raise except_orm(
                _('Data error!'),
                _("You need to specify a link to " +
                  self.name.application_id.name + " for the service " +
                  self.service_id.name))

    # def get_vals(self, cr, uid, id, context={}):
    #     vals = {}
    #
    #     link = self.browse(cr, uid, id, context=context)
    #
    #     vals.update(self.pool.get('clouder.service').get_vals(cr, uid, link.service_id.id, context=context))
    #     if link.target:
    #         target_vals = self.pool.get('clouder.container').get_vals(cr, uid, link.target.id, context=context)
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
    #
    # @api.multi
    # def reload(self):
    #     for link_id in ids:
    #         vals = self.get_vals(cr, uid, link_id, context=context)
    #         self.deploy(cr, uid, vals, context=context)
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
        app_links = self.env['clouder.application.link'].search([
            ('application_id', '=', self.service_id.application_id.id),
            ('name.code', '=', self.target.application_id.code)])
        if not app_links:
            self.log('The target isnt in the application link for service, '
                     'skipping deploy link')
            return False
        if not app_links[0].service:
            self.log('This application isnt for service, skipping deploy link')
            return False
        return True

    @api.multi
    def deploy_(self):
        self.purge_()
        self.control() and self.deploy_link()

    @api.multi
    def purge_(self):
        self.control() and self.purge_link()