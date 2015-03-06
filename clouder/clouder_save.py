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

from datetime import datetime
import ast

import logging

_logger = logging.getLogger(__name__)


class ClouderSaveRepository(models.Model):
    _name = 'clouder.save.repository'

    name = fields.Char('Name', size=128, required=True)
    type = fields.Selection([('container', 'Container'), ('base', 'Base')],
                            'Name', required=True)
    date_change = fields.Date('Change Date')
    date_expiration = fields.Date('Expiration Date')
    container_name = fields.Char('Container Name', size=64)
    container_server = fields.Char('Container Server', size=128)
    base_name = fields.Char('Base Name', size=64)
    base_domain = fields.Char('Base Domain', size=128)
    save_ids = fields.One2many('clouder.save.save', 'repo_id', 'Saves')

    _order = 'create_date desc'

    # @api.multi
    # def get_vals(self):
    #
    #     vals = {}
    #
    #     vals.update(self.env.ref('clouder.clouder_settings').get_vals())
    #
    #     vals.update({
    #         'saverepo_id': self.id,
    #         'saverepo_name': self.name,
    #         'saverepo_type': self.type,
    #         'saverepo_date_change': self.date_change,
    #         'saverepo_date_expiration': self.date_expiration,
    #         'saverepo_container_name': self.container_name,
    #         'saverepo_container_server': self.container_server,
    #         'saverepo_base_name': self.base_name,
    #         'saverepo_base_domain': self.base_domain,
    #     })
    #
    #     return vals


class ClouderSaveSave(models.Model):
    _name = 'clouder.save.save'
    _inherit = ['clouder.model']

    name = fields.Char('Name', size=256, required=True)
    type = fields.Selection([('container', 'Container'), ('base', 'Base')],
                            'Type', related='repo_id.type', readonly=True)
    backup_id = fields.Many2one(
        'clouder.container', 'Backup Server', required=True)
    repo_id = fields.Many2one('clouder.save.repository', 'Repository',
                              ondelete='cascade', required=True)
    date_expiration = fields.Date('Expiration Date')
    comment = fields.Text('Comment')
    now_bup = fields.Char('Now bup', size=64)
    container_id = fields.Many2one('clouder.container', 'Container')
    container_volumes_comma = fields.Text('Container Volumes comma')
    container_app = fields.Char('Application', size=64)
    container_img = fields.Char('Image', size=64)
    container_img_version = fields.Char('Image Version', size=64)
    container_ports = fields.Text('Ports')
    container_volumes = fields.Text('Volumes')
    container_volumes_comma = fields.Text('Volumes comma')
    container_options = fields.Text('Container Options')
    container_links = fields.Text('Container Links')
    service_id = fields.Many2one('clouder.service', 'Service')
    service_name = fields.Char('Service Name', size=64)
    service_app_version = fields.Char('Application Version', size=64)
    service_options = fields.Text('Service Options')
    service_links = fields.Text('Service Links')
    base_id = fields.Many2one('clouder.base', 'Base')
    base_title = fields.Char('Title', size=64)
    base_container_name = fields.Char('Container', size=64)
    base_container_server = fields.Char('Server', size=64)
    base_admin_passwd = fields.Char('Admin passwd', size=64)
    base_poweruser_name = fields.Char('Poweruser name', size=64)
    base_poweruser_password = fields.Char('Poweruser Password', size=64)
    base_poweruser_email = fields.Char('Poweruser email', size=64)
    base_build = fields.Char('Build', size=64)
    base_test = fields.Boolean('Test?')
    base_lang = fields.Char('Lang', size=64)
    base_nosave = fields.Boolean('No save?')
    base_options = fields.Text('Base Options')
    base_links = fields.Text('Base Links')
    container_name = fields.Char(
        'Container Name', related='repo_id.container_name',
        size=64, readonly=True)
    container_server = fields.Char(
        'Container Server', related='repo_id.container_server',
        type='char', size=64, readonly=True)
    container_restore_to_name = fields.Char('Restore to (Name)', size=64)
    container_restore_to_server_id = fields.Many2one(
        'clouder.server', 'Restore to (Server)')
    base_name = fields.Char(
        'Base Name', related='repo_id.base_name',
        type='char', size=64, readonly=True)
    base_domain = fields.Char(
        'Base Domain', related='repo_id.base_domain',
        type='char', size=64, readonly=True)
    base_restore_to_name = fields.Char('Restore to (Name)', size=64)
    base_restore_to_domain_id = fields.Many2one(
        'clouder.domain', 'Restore to (Domain)')
    create_date = fields.Datetime('Create Date')

    @property
    def now_epoch(self):
        return (datetime.strptime(self.now_bup, "%Y-%m-%d-%H%M%S") -
                datetime(1970, 1, 1)).total_seconds()

    @property
    def backup_method(self):
        return self.backup_id.options['backup_method']['value']

    @property
    def base_dumpfile(self):
        return \
            self.repo_id.type == 'base' \
            and self.container_app + '_' + self.base_name.replace('-', '_') + \
                '_' + self.base_domain.replace('-', '_').replace('.', '_') + \
                '.dump'

    @property
    def computed_container_restore_to_name(self):
        return self.container_restore_to_name or self.base_container_name \
               or self.repo_id.container_name

    @property
    def computed_container_restore_to_server(self):
        return self.container_restore_to_server_id.name \
               or self.base_container_server or self.repo_id.container_server

    @property
    def computed_base_restore_to_name(self):
        return self.base_restore_to_name or self.repo_id.base_name

    @property
    def computed_base_restore_to_domain(self):
        return self.base_restore_to_domain_id.name or self.repo_id.base_domain

    _order = 'create_date desc'

    # @api.multi
    # def get_vals(self):
    #     vals = {}
    #
    #     if self.base_id:
    #         vals.update(self.base_id.get_vals())
    #     elif self.service_id:
    #         vals.update(self.service_id.get_vals())
    #     elif self.container_id:
    #         vals.update(self.container_id.get_vals())
    #
    #     vals.update(self.repo_id.get_vals())
    #
    #     backup_server_vals = self.backup_id.get_vals()
    #     vals.update({
    #         'backup_id': backup_server_vals['container_id'],
    #         'backup_fullname': backup_server_vals['container_fullname'],
    #         'backup_id': backup_server_vals['server_id'],
    #         'backup_server_ssh_port': backup_server_vals['server_ssh_port'],
    #         'backup_server_domain': backup_server_vals['server_domain'],
    #         'backup_server_ip': backup_server_vals['server_ip'],
    #         'backup_method': backup_server_vals['app_options']['backup_method']['value']
    #     })
    #
    #     vals.update({
    #         'save_id': self.id,
    #         'save_name': self.name,
    #         'saverepo_date_expiration': self.date_expiration,
    #         'save_comment': self.comment,
    #         'save_now_bup': self.now_bup,
    #         'save_now_epoch': (datetime.strptime(self.now_bup, "%Y-%m-%d-%H%M%S") - datetime(1970,1,1)).total_seconds(),
    #         'save_base_id': self.base_id.id,
    #         'save_container_volumes': self.container_volumes_comma,
    #         'save_container_restore_to_name': self.container_restore_to_name or self.base_container_name or vals['saverepo_container_name'],
    #         'save_container_restore_to_server': self.container_restore_to_server_id.name or self.base_container_server or vals['saverepo_container_server'],
    #         'save_base_restore_to_name': self.base_restore_to_name or vals['saverepo_base_name'],
    #         'save_base_restore_to_domain': self.base_restore_to_domain_id.name or vals['saverepo_base_domain'],
    #         'save_base_dumpfile': vals['saverepo_type'] == 'base' and self.container_app + '_' + self.base_name.replace('-','_') + '_' + self.base_domain.replace('-','_').replace('.','_') + '.dump'
    #     })
    #     return vals

    @api.multi
    def create(self, vals):
        if 'container_id' in vals:
            container = self.env['clouder.container'] \
                .browse(vals['container_id'])

            container_ports = {}
            for port in container.port_ids:
                container_ports[port.name] = {
                    'name': port.name, 'localport': port.localport,
                    'expose': port.expose, 'udp': port.udp}

            container_volumes = {}
            for volume in container.volume_ids:
                container_volumes[volume.id] = {
                    'name': volume.name, 'hostpath': volume.hostpath,
                    'user': volume.user, 'readonly': volume.readonly,
                    'nosave': volume.nosave}

            container_links = {}
            for link in container.link_ids:
                container_links[link.name.code] = {
                    'name': link.name.id,
                    'code': link.name.code,
                    'target': link.target and link.target.id
                }

            vals.update({
                'container_volumes_comma': container.volumes_save,
                'container_app': container.application_id.code,
                'container_img': container.image_id.name,
                'container_img_version': container.image_version_id.name,
                'container_ports': str(container_ports),
                'container_volumes': str(container_volumes),
                'container_options': str(container.options),
                'container_links': str(container_links),
            })

        if 'service_id' in vals:
            service = self.env['clouder.service'].browse(vals['service_id'])

            service_links = {}
            for link in service.link_ids:
                service_links[link.name.code] = {
                    'name': link.name.id,
                    'code': link.name.code,
                    'target': link.target and link.target.id
                }

            vals.update({
                'service_name': service.name,
                'service_app_version': service.application_version_id.name,
                'service_options': str(service.options),
                'service_links': str(service_links),
            })

        if 'base_id' in vals:
            base = self.env['clouder.base'].browse(vals['base_id'])

            base_links = {}
            for link in base.link_ids:
                base_links[link.name.code] = {
                    'name': link.name.id,
                    'code': link.name.code,
                    'target': link.target and link.target.id
                }

            vals.update({
                'base_title': base.title,
                'base_container_name': base.service_id.container_id.name,
                'base_container_server':
                base.service_id.container_id.server_id.name,
                'base_admin_passwd': base.admin_passwd,
                'base_poweruser_name': base.poweruser_name,
                'base_poweruser_password': base.poweruser_password,
                'base_poweruser_email': base.poweruser_email,
                'base_build': base.build,
                'base_test': base.test,
                'base_lang': base.lang,
                'base_nosave': base.nosave,
                'base_options': str(base.options),
                'base_links': str(base_links),
            })

        return super(ClouderSaveSave, self).create(vals)

    @api.multi
    def purge(self):
        ssh = self.connect(self.backup_id.fullname)
        self.execute(ssh, ['rm', '-rf', '/opt/backup/simple/' +
                           self.repo_id.name + '/' + self.name])
        if self.search([('repo_id', '=', self.repo_id)]) == [self]:
            self.execute(ssh, ['rm', '-rf', '/opt/backup/simple/' +
                               self.repo_id.name])
            self.execute(ssh, ['git', '--git-dir=/opt/backup/bup',
                               'branch', '-D', self.repo_id.name])
        ssh.close()
        return

    @api.multi
    def restore_base(self):
        return

    def restore(self):
        container_obj = self.env['clouder.container']
        base_obj = self.env['clouder.base']
        server_obj = self.env['clouder.server']
        domain_obj = self.env['clouder.domain']
        application_obj = self.env['clouder.application']
        application_version_obj = self.env['clouder.application.version']
        application_link_obj = self.env['clouder.application.link']
        image_obj = self.env['clouder.image']
        image_version_obj = self.env['clouder.image.version']
        service_obj = self.env['clouder.service']

        self = self.with_context(self.create_log('restore'))

        apps = application_obj.search([('code', '=', self.container_app)])
        if not apps:
            raise except_orm(
                _('Error!'),
                _("Couldn't find application " + self.container_app +
                  ", aborting restoration."))
        imgs = image_obj.search([('name', '=', self.container_img)])
        if not imgs:
            raise except_orm(
                _('Error!'),
                _("Couldn't find image " + self.container_img +
                  ", aborting restoration."))

        img_versions = image_version_obj.search(
            [('name', '=', self.container_img_version)])
        # upgrade = True
        if not img_versions:
            self.log("Warning, couldn't find the image version, using latest")
            #We do not want to force the upgrade if we had to use latest
            # upgrade = False
            versions = imgs[0].version_ids
            if not versions:
                raise except_orm(
                    _('Error!'),
                    _("Couldn't find versions for image " +
                      self.container_img + ", aborting restoration."))
            img_versions = [versions[0]]

        if self.container_restore_to_name or not self.container_id:
            containers = container_obj.search([
                ('name', '=', self.computed_container_restore_to_name),
                ('server_id.name', '=',
                 self.computed_container_restore_to_server)
            ])

            if not containers:
                self.log("Can't find any corresponding container, "
                         "creating a new one")
                servers = server_obj.search([
                    ('name', '=', self.computed_container_restore_to_server)])
                if not servers:
                    raise except_orm(
                        _('Error!'),
                        _("Couldn't find server " +
                          self.computed_container_restore_to_server +
                          ", aborting restoration."))

                ports = []
                for port, port_vals \
                        in ast.literal_eval(self.container_ports).iteritems():
                    ports.append((0, 0, port_vals))
                volumes = []
                for volume, volume_vals in \
                        ast.literal_eval(self.container_volumes).iteritems():
                    volumes.append((0, 0, volume_vals))
                options = []
                for option, option_vals in \
                        ast.literal_eval(self.container_options).iteritems():
                    del option_vals['id']
                    options.append((0, 0, option_vals))
                links = []
                for link, link_vals in ast.literal_eval(
                        self.container_links).iteritems():
                    if not link_vals['name']:
                        link_apps = application_link_obj.search([
                            ('name.code', '=', link_vals['code']),
                            ('application_id', '=', apps[0])])
                        if link_apps:
                            link_vals['name'] = link_apps[0]
                        else:
                            continue
                    links.append((0, 0, link_vals))
                container_vals = {
                    'name': self.computed_container_restore_to_name,
                    'server_id': servers[0],
                    'application_id': apps[0],
                    'image_id': imgs[0],
                    'image_version_id': img_versions[0],
                    'port_ids': ports,
                    'volume_ids': volumes,
                    'option_ids': options,
                    'link_ids': links
                }
                container = container_obj.create(container_vals)

            else:
                self.log("A corresponding container was found")
                container = containers[0]
        else:
            self.log("A container_id was linked in the save")
            container = self.container_id

        if self.repo_id.type == 'container':
            # vals = self.get_vals(cr, uid, save.id, context=context)
            # vals_container = container_obj.get_vals(cr, uid, container_id, context=context)
            if container.image_version_id != img_versions[0]:
                # if upgrade:
                container.image_version_id = img_versions[0]
                self = self.with_context(forcesave=False)
                self = self.with_context(nosave=True)

            self = self.with_context(
                save_comment='Before restore ' + self.name)
            container.save()

            # vals = self.get_vals(cr, uid, save.id, context=context)
            # vals_container = container_obj.get_vals(cr, uid, container_id, context=con
            ssh = self.connect(container.fullname)
            self.execute(ssh, ['supervisorctl', 'stop', 'all'])
            self.execute(ssh, ['supervisorctl', 'start', 'sshd'])
            self.restore_action(container)
            # ssh = execute.connect(vals['saverepo_container_server'], 22, 'root', context)
            # execute.execute(ssh, ['docker', 'run', '-t', '--rm', '--volumes-from', vals['saverepo_container_name'], '-v', '/opt/keys/bup:/root/.ssh', 'img_bup:latest', '/opt/restore', 'container', vals['saverepo_name'], vals['save_now_bup'], vals['save_container_volumes']], context)
            # ssh.close()
            # sftp.close()


            for volume in container.volume_ids:
                if volume.user:
                    self.execute(ssh, ['chown', '-R',
                                       volume.user + ':' + volume.user,
                                       volume.name])
            # execute.execute(ssh, ['supervisorctl', 'start', 'all'], context)
            ssh.close()
            container.start()

            container.deploy_links()
            self.end_log()
            res = container


        else:
            # upgrade = False
            app_versions = application_version_obj.search(
                [('name', '=', self.base_app_version),
                 ('application_id', '=', apps[0])])
            if not app_versions:
                self.log(
                    "Warning, couldn't find the application version, "
                    "using latest")
                #We do not want to force the upgrade if we had to use latest
                # upgrade = False
                versions = application_obj.browse(apps[0]).version_ids
                if not versions:
                    raise except_orm(
                        _('Error!'),
                        _("Couldn't find versions for application " +
                          self.container_app + ", aborting restoration."))
                app_versions = [versions[0]]
            if not self.service_id or self.service_id.container_id != container:
                services = service_obj.search(
                    [('name', '=', self.service_name),
                     ('container_id.id', '=', container)])

                if not services:
                    self.log("Can't find any corresponding service, "
                             "creating a new one")
                    options = []
                    for option, option_vals in ast.literal_eval(
                            self.service_options).iteritems():
                        del option_vals['id']
                        options.append((0, 0, option_vals))
                    links = []
                    for link, link_vals in ast.literal_eval(
                            self.service_links).iteritems():
                        if not link_vals['name']:
                            link_apps = application_link_obj.search(
                                [('name.code', '=', link_vals['code']),
                                 ('application_id', '=', apps[0])])
                            if link_apps:
                                link_vals['name'] = link_apps[0]
                            else:
                                continue
                        del link_vals['name_name']
                        links.append((0, 0, link_vals))
                    service_vals = {
                        'name': self.service_name,
                        'container_id': container,
                        'database_container_id': self.service_database_id.id,
                        'application_version_id': app_versions[0],
                        'option_ids': options,
                        'link_ids': links
                    }
                    service = service_obj.create(service_vals)

                else:
                    self.log("A corresponding service was found")
                    service = services[0]
            else:
                self.log("A service_id was linked in the save")
                service = self.service_id

            if self.base_restore_to_name or not self.base_id:
                bases = base_obj.search(
                    [('name', '=', self.computed_base_restore_to_name), (
                        'domain_id.name', '=',
                        self.computed_base_restore_to_domain)])

                if not bases:
                    self.log(
                        "Can't find any corresponding base, "
                        "creating a new one")
                    domains = domain_obj.search(
                        [('name', '=', self.computed_base_restore_to_domain)])
                    if not domains:
                        raise except_orm(
                            _('Error!'),
                            _("Couldn't find domain " +
                              self.computed_base_restore_to_domain +
                              ", aborting restoration."))
                    options = []
                    for option, option_vals in ast.literal_eval(
                            self.base_options).iteritems():
                        del option_vals['id']
                        options.append((0, 0, option_vals))
                    links = []
                    for link, link_vals in ast.literal_eval(
                            self.base_links).iteritems():
                        if not link_vals['name']:
                            link_apps = application_link_obj.search(
                                [('name.code', '=', link_vals['code']),
                                 ('application_id', '=', apps[0])])
                            if link_apps:
                                link_vals['name'] = link_apps[0]
                            else:
                                continue
                        del link_vals['name_name']
                        links.append((0, 0, link_vals))
                    base_vals = {
                        'name': self.computed_base_restore_to_name,
                        'service_id': service,
                        'application_id': apps[0],
                        'domain_id': domains[0],
                        'title': self.base_title,
                        'admin_passwd': self.base_admin_passwd,
                        'poweruser_name': self.base_poweruser_name,
                        'poweruser_passwd': self.base_poweruser_password,
                        'poweruser_email': self.base_poweruser_email,
                        'build': self.base_build,
                        'test': self.base_test,
                        'lang': self.base_lang,
                        'nosave': self.base_nosave,
                        'option_ids': options,
                        'link_ids': links,
                    }
                    self = self.with_context(base_restoration=True)
                    base = base_obj.create(base_vals)

                else:
                    self.log("A corresponding base was found")
                    base = bases[0]
            else:
                self.log("A base_id was linked in the save")
                base = self.base_id.id

            if base.service_id.application_version_id != app_versions[0]:
                # if upgrade:
                base.application_version_id = app_versions[0]

            self = self.with_context(
                save_comment='Before restore ' + self.name)
            base.save()

            self.restore_action(base)

            base.purge_db()
            ssh = self.connect(
                base.service_id.container_id.fullname,
                username=base.application_id.type_id.system_user)
            for key, database in base.databases().iteritems():
                if base.service_id.database_type() != 'mysql':
                    self.execute(ssh, ['createdb', '-h',
                                       base.service_id.database_server(), '-U',
                                       base.service_id.db_user(),
                                       base.fullname_])
                    self.execute(ssh, ['cat',
                                       '/base-backup/' + self.repo_id.name
                                       + '/' + self.base_dumpfile,
                                       '|', 'psql', '-q', '-h',
                                       base.service_id.database_server(), '-U',
                                       base.service_id.db_user(),
                                       base.fullname_])
                else:
                    ssh_mysql, sftp_mysql = self.connect(
                        base.service_id.database().fullname)
                    self.execute(ssh_mysql, [
                        "mysql -u root -p'" +
                        base.service_id.database().root_password +
                        "' -se \"create database " + database + ";\""])
                    self.execute(ssh_mysql, [
                        "mysql -u root -p'" +
                        base.service_id.database().root_password +
                        "' -se \"grant all on " + database + ".* to '" +
                        base.service_id.db_user() + "';\""])
                    ssh_mysql.close(), sftp_mysql.close()
                    self.execute(ssh, [
                        'mysql', '-h', base.service_id.database_server(), '-u',
                        base.service_id.db_user(),
                        '-p' + base.service_id.database_password, database,
                        '<', '/base-backup/' + self.repo_id.name + '/' +
                        database + '.dump'])

            self.restore_base()

            base_obj.deploy_links()

            self.execute(ssh,
                         ['rm', '-rf', '/base-backup/' + self.repo_id.name])
            ssh.close()

            self.end_log()
            res = base
        self.write({'container_restore_to_name': False,
                    'container_restore_to_server_id': False,
                    'base_restore_to_name': False,
                    'base_restore_to_domain_id': False})

        return res

    @api.multi
    def restore_action(self, object):
        #
        # context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        # ssh = execute.connect(vals['save_computed_container_restore_to_server'], 22, 'root', context)
        # execute.execute(ssh, ['docker', 'run', '-t', '--rm', '--volumes-from', vals['save_computed_container_restore_to_name'], '-v', '/opt/keys/bup:/root/.ssh', 'img_bup:latest', '/opt/restore', 'base', vals['saverepo_name'], vals['save_now_bup']], context)
        # ssh.close()
        # sftp.close()
        #

        if object._name == 'clouder.base':
            container = object.service_id.container_id
        else:
            container = object

        directory = '/tmp/restore-' + self.repo_id.name
        ssh = self.connect(self.backup_id.fullname, username='backup')
        self.send(ssh, self.home_directory + '/.ssh/config',
                  '/home/backup/.ssh/config')
        self.send(ssh,
                  self.home_directory + '/.ssh/keys/' +
                  container.fullname + '.pub',
                  '/home/backup/.ssh/keys/' + container.fullname + '.pub')
        self.send(ssh,
                  self.home_directory + '/.ssh/keys/' + container.fullname,
                  '/home/backup/.ssh/keys/' + container.fullname)
        self.execute(ssh, ['chmod', '-R', '700', '/home/backup/.ssh'])
        self.execute(ssh, ['rm', '-rf', directory + '*'])
        self.execute(ssh, ['mkdir', '-p', directory])

        if self.backup_method() == 'simple':
            self.execute(ssh, [
                'cp', '-R', '/opt/backup/simple/' + self.repo_id.name +
                '/' + self.name + '/*', directory])

        if self.backup_method() == 'bup':
            self.execute(ssh, [
                'export BUP_DIR=/opt/backup/bup;',
                'bup restore -C ' + directory + ' ' + self.repo_id.name +
                '/' + self.now_bup])
            self.execute(ssh, [
                'mv', directory + '/' + self.now_bup + '/*', directory])
            self.execute(ssh, ['rm -rf', directory + '/' + self.now_bup])

        self.execute(ssh, ['rsync', '-ra', directory + '/',
                           container.fullname + ':' + directory])
        self.execute(ssh, ['rm', '-rf', directory + '*'])
        self.execute(ssh, ['rm', '/home/backup/.ssh/keys/*'])
        ssh.close()

        ssh = self.connect(container.fullname)

        if self.repo_id.type == 'container':
            for volume in container.volume_ids:
                self.execute(ssh, ['rm', '-rf', volume.name + '/*'])
        else:
            self.execute(ssh,
                         ['rm', '-rf', '/base-backup/' + self.repo_id.name])

        self.execute(ssh, ['rm', '-rf', directory + '/backup-date'])
        if self.repo_id.type == 'container':
            self.execute(ssh, ['cp', '-R', directory + '/*', '/'])
        else:
            self.execute(ssh, ['cp', '-R', directory,
                               '/base-backup/' + self.repo_id.name])
            self.execute(ssh, ['chmod', '-R', '777',
                               '/base-backup/' + self.repo_id.name])
        self.execute(ssh, ['rm', '-rf', directory + '*'])
        ssh.close()

    @api.multi
    def deploy_base(self):
        return

    @api.multi
    def deploy(self):
        self.log('Saving ' + self.name)
        self.log('Comment: ' + self.comment)

        if self.repo_id.type == 'base' and self.base_id:
            base = self.base_id
            ssh = self.connect(
                base.service_id.container_id.fullname,
                username=base.application_id.type_id.system_user)
            self.execute(ssh,
                         ['mkdir', '-p', '/base-backup/' + self.repo_id.name])
            for key, database in base.databases().iteritems():
                if base.service_id.database_type() != 'mysql':
                    self.execute(ssh, [
                        'pg_dump', '-O', ''
                        '-h', base.service_id.database_server(),
                        '-U', base.service_id.db_user(), database,
                        '>', '/base-backup/' + self.repo_id.name + '/' +
                        database + '.dump'])
                else:
                    self.execute(ssh, [
                        'mysqldump',
                        '-h', base.service_id.database_server(),
                        '-u', base.service_id.db_user(),
                        '-p' + base.service_id.database_password(),
                        database, '>', '/base-backup/' + self.repo_id.name +
                        '/' + database + '.dump'])
            base.deploy_base()
            self.execute(ssh, ['chmod', '-R', '777',
                               '/base-backup/' + self.repo_id.name])
            ssh.close()

        #
        # ssh = execute.connect(vals['save_computed_container_restore_to_server'], 22, 'root', context)
        # execute.execute(ssh, ['docker', 'run', '-t', '--rm', '--volumes-from', vals['save_computed_container_restore_to_name'], '-v', '/opt/keys/bup:/root/.ssh', 'img_bup:latest', '/opt/save', vals['saverepo_type'], vals['saverepo_name'], str(int(vals['save_now_epoch'])), vals['save_container_volumes'] or ''], context)
        # ssh.close()
        # sftp.close()

        directory = '/tmp/' + self.repo_id.name
        ssh = self.connect(self.container_id.fullname)
        self.execute(ssh, ['rm', '-rf', directory + '*'])
        self.execute(ssh, ['mkdir', directory])
        if self.repo_id.type == 'container':
            for volume in self.container_volumes.split(','):
                self.execute(ssh, ['cp', '-R', '--parents', volume, directory])
        else:
            self.execute(ssh, ['cp', '-R',
                               '/base-backup/' + self.repo_id.name + '/*',
                               directory])

        self.execute(ssh, [
            'echo "' + self.now_date() + '" > ' + directory + '/backup-date'])
        self.execute(ssh, ['chmod', '-R', '777', directory + '*'])
        ssh.close()

        ssh = self.connect(self.backup_id.fullname, username='backup')
        if self.repo_id.type == 'container':
            name = self.container_id.fullname
        else:
            name = self.base_id.fullname_
        self.execute(ssh, ['rm', '-rf', '/opt/backup/list/' + name])
        self.execute(ssh, ['mkdir', '-p', '/opt/backup/list/' + name])
        self.execute(ssh, [
            'echo "' + self.repo_id.name +
            '" > /opt/backup/list/' + name + '/repo'])

        self.send(ssh, self.home_directory + '/.ssh/config',
                  '/home/backup/.ssh/config')
        self.send(ssh,
                  self.home_directory + '/.ssh/keys/' +
                  self.container_id.fullname + '.pub',
                  '/home/backup/.ssh/keys/' +
                  self.container_id.fullname + '.pub')
        self.send(ssh,
                  self.home_directory + '/.ssh/keys/' +
                  self.container_id.fullname,
                  '/home/backup/.ssh/keys/' +
                  self.container_id.fullname)
        self.execute(ssh, ['chmod', '-R', '700', '/home/backup/.ssh'])

        self.execute(ssh, ['rm', '-rf', directory])
        self.execute(ssh, ['mkdir', directory])
        self.execute(ssh, [
            'rsync', '-ra',
            self.container_id.fullname + ':' + directory + '/', directory])

        if self.backup_method() == 'simple':
            self.execute(ssh, [
                'mkdir', '-p', '/opt/backup/simple/' +
                self.repo_id.name + '/' + self.name])
            self.execute(ssh, [
                'cp', '-R', directory + '/*',
                '/opt/backup/simple/' + self.repo_id.name + '/' + self.name])
            self.execute(ssh, [
                'rm', '/opt/backup/simple/' + self.repo.name + '/latest'])
            self.execute(ssh, [
                'ln', '-s',
                '/opt/backup/simple/' + self.repo.name + '/' + self.name,
                '/opt/backup/simple/' + self.repo_id.name + '/latest'])

        if self.backup_method() == 'bup':
            self.execute(ssh, ['export BUP_DIR=/opt/backup/bup;',
                               'bup index ' + directory])
            self.execute(ssh, [
                'export BUP_DIR=/opt/backup/bup;',
                'bup save -n ' + self.repo_id.name + ' -d ' +
                str(int(self.now_epoch)) + ' --strip ' + directory])

        self.execute(ssh, ['rm', '-rf', directory + '*'])
        self.execute(ssh, ['rm', '/home/backup/.ssh/keys/*'])
        ssh.close()

        ssh = self.connect(self.container_id.fullname)
        self.execute(ssh, ['rm', '-rf', directory + '*'])
        ssh.close()

        if self.repo.type == 'base':
            ssh = self.connect(
                self.base_id.service_id.container_id.fullname,
                username=self.base_id.application_id.type_id.system_user)
            self.execute(ssh,
                         ['rm', '-rf', '/base-backup/' + self.repo_id.name])
            ssh.close()
        return

