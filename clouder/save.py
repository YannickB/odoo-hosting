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

from datetime import datetime
import ast
import os

import logging

_logger = logging.getLogger(__name__)


class ClouderSave(models.Model):
    """
    Define the save.save object, which represent the saves of containers/bases.
    """

    _name = 'clouder.save'
    _inherit = ['clouder.model']

    name = fields.Char('Name', required=True)
    backup_id = fields.Many2one(
        'clouder.container', 'Backup Server', required=True)
    date_expiration = fields.Date('Expiration Date')
    comment = fields.Text('Comment')
    now_bup = fields.Char('Now bup')
    environment = fields.Char(
        'Environment', readonly=True)
    container_id = fields.Many2one('clouder.container', 'Container')
    container_fullname = fields.Char('Container Fullname')
    container_app = fields.Char('Application')
    container_img = fields.Char('Image')
    container_img_version = fields.Char('Image Version')
    container_ports = fields.Text('Ports')
    container_volumes = fields.Text('Volumes')
    container_volumes_comma = fields.Text('Volumes comma')
    container_options = fields.Text('Container Options')
    container_links = fields.Text('Container Links')
    base_id = fields.Many2one('clouder.base', 'Base')
    base_fullname = fields.Char('Base Fullname')
    base_title = fields.Char('Title')
    base_container_suffix = fields.Char('Container Name')
    base_container_server = fields.Char('Server')
    base_admin_name = fields.Char('Admin name')
    base_admin_password = fields.Char('Admin passwd')
    base_admin_email = fields.Char('Admin email')
    base_poweruser_name = fields.Char('Poweruser name')
    base_poweruser_password = fields.Char('Poweruser Password')
    base_poweruser_email = fields.Char('Poweruser email')
    base_build = fields.Char('Build')
    base_test = fields.Boolean('Test?')
    base_lang = fields.Char('Lang')
    base_autosave = fields.Boolean('Save?')
    base_options = fields.Text('Base Options')
    base_links = fields.Text('Base Links')
    container_suffix = fields.Char(
        'Container Suffix', readonly=True)
    container_server = fields.Char(
        'Container Server',
        type='char', readonly=True)
    restore_to_environment_id = fields.Many2one(
        'clouder.environment', 'Restore to (Environment)')
    container_restore_to_suffix = fields.Char('Restore to (Suffix)')
    container_restore_to_server_id = fields.Many2one(
        'clouder.server', 'Restore to (Server)')
    base_name = fields.Char(
        'Base Name',
        type='char', readonly=True)
    base_domain = fields.Char(
        'Base Domain',
        type='char', readonly=True)
    base_restore_to_name = fields.Char('Restore to (Name)')
    base_restore_to_domain_id = fields.Many2one(
        'clouder.domain', 'Restore to (Domain)')
    create_date = fields.Datetime('Create Date')

    @property
    def now_epoch(self):
        """
        Property returning the actual time, at the epoch format.
        """
        return (datetime.strptime(self.now_bup, "%Y-%m-%d-%H%M%S") -
                datetime(1970, 1, 1)).total_seconds()

    @property
    def base_dumpfile(self):
        """
        Property returning the dumpfile name.
        """
        return self.base_fullname.replace('.', '_').replace('-', '_') + '.dump'

    @property
    def computed_restore_to_environment(self):
        """
        Property returning the environment which will be restored.
        """
        return self.restore_to_environment_id.prefix \
            or self.environment

    @property
    def computed_container_restore_to_suffix(self):
        """
        Property returning the container suffix which will be restored.
        """
        return self.container_restore_to_suffix or self.base_container_suffix \
            or self.repo_id.container_suffix

    @property
    def computed_container_restore_to_server(self):
        """
        Property returning the container server which will be restored.
        """
        return self.container_restore_to_server_id.fulldomain \
            or self.base_container_server or self.repo_id.container_server

    @property
    def computed_base_restore_to_name(self):
        """
        Property returning the base name which will be restored.
        """
        return self.base_restore_to_name or self.repo_id.base_name

    @property
    def computed_base_restore_to_domain(self):
        """
        Property returning the base domain which will be restored.
        """
        return self.base_restore_to_domain_id.name or self.repo_id.base_domain

    @property
    def repo_name(self):
        repo_name = self.container_fullname
        if self.base_fullname:
            repo_name = self.base_fullname
        return repo_name

    _order = 'create_date desc'

    @api.multi
    def create(self, vals):
        """
        Override create method to add the data in container and base in the
        save record, so we can restore it if the container/service/base are
        deleted.

        :param vals: The values we need to create the record.
        """
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
                    'target': link.target and link.target.id or False
                }

            vals.update({
                'environment': container.environment_id.prefix,
                'container_fullname': container.fullname,
                'container_suffix': container.suffix,
                'container_server': container.server_id.fulldomain,
                'container_volumes_comma': container.volumes_save,
                'container_app': container.application_id.code,
                'container_img': container.image_id.name,
                'container_img_version': container.image_version_id.name,
                'container_ports': str(container_ports),
                'container_volumes': str(container_volumes),
                'container_options': str(container.options),
                'container_links': str(container_links),
            })

        if 'base_id' in vals:
            base = self.env['clouder.base'].browse(vals['base_id'])

            base_links = {}
            for link in base.link_ids:
                base_links[link.name.code] = {
                    'name': link.name.id,
                    'code': link.name.code,
                    'target': link.target and link.target.id or False
                }

            vals.update({
                'environment': base.environment_id.prefix,
                'base_fullname': base.fullname,
                'base_name': base.name,
                'base_domain': base.domain_id.name,
                'base_title': base.title,
                'base_container_environment':
                    base.container_id.environment_id.prefix,
                'base_container_suffix': base.container_id.suffix,
                'base_container_server':
                base.container_id.server_id.fulldomain,
                'base_admin_name': base.admin_name,
                'base_admin_password': base.admin_password,
                'base_admin_email': base.admin_email,
                'base_poweruser_name': base.poweruser_name,
                'base_poweruser_password': base.poweruser_password,
                'base_poweruser_email': base.poweruser_email,
                'base_build': base.build,
                'base_test': base.test,
                'base_lang': base.lang,
                'base_autosave': base.autosave,
                'base_options': str(base.options),
                'base_links': str(base_links),
            })

        return super(ClouderSave, self).create(vals)

    @api.multi
    def save_database(self):
        """

        :return:
        """
        return

    @api.multi
    def deploy_base(self):
        """
        Hook which can be called by submodules to execute commands after we
        restored a base.
        """
        return

    @api.multi
    def deploy(self):
        """
        Build the save and move it into the backup container.
        """
        self.log('Saving ' + self.name)
        self.log('Comment: ' + self.comment)

        container = 'exec' in self.container_id.childs \
                    and self.container_id.childs['exec'] or self.container_id
        if self.base_fullname:
            container = container.base_backup_container
            container.execute([
                'mkdir', '-p', '/base-backup/' + self.name],
                username='root')

            container.execute(['chmod', '-R', '777',
                               '/base-backup/' + self.name], username='root')
            self.save_database()
            self.deploy_base()

        directory = '/tmp/clouder/' + self.name
        container.server_id.execute(['rm', '-rf', directory + '/*'])
        container.server_id.execute(['mkdir', directory])
        if self.base_fullname:
            container.server_id.execute([
                'docker', 'cp',
                container.name + ':/base-backup/' + self.name,
                '/tmp/clouder'])
        else:
            for volume in self.container_volumes_comma.split(','):
                container.server_id.execute([
                    'mkdir', '-p', directory + volume])
                container.server_id.execute([
                    'docker', 'cp',
                    container.name + ':' + volume,
                    directory + os.path.split(volume)[0]])

        container.server_id.execute([
            'echo "' + self.now_date + '" > ' + directory + '/backup-date'])
        container.server_id.execute(['chmod', '-R', '777', directory + '*'])

        backup = self.backup_id
        if self.base_fullname:
            name = self.base_id.fullname_
        else:
            name = self.container_id.fullname
        backup.execute(['rm', '-rf', '/opt/backup/list/' + name],
                       username='backup')
        backup.execute(['mkdir', '-p', '/opt/backup/list/' + name],
                       username='backup')
        backup.execute([
            'echo "' + self.repo_name +
            '" > /opt/backup/list/' + name + '/repo'], username='backup')

        backup.send(self.home_directory + '/.ssh/config',
                    '/home/backup/.ssh/config', username='backup')
        backup.send(
            self.home_directory + '/.ssh/keys/' +
            self.container_id.server_id.fulldomain + '.pub',
            '/home/backup/.ssh/keys/' +
            self.container_id.server_id.fulldomain + '.pub', username='backup')
        backup.send(
            self.home_directory + '/.ssh/keys/' +
            self.container_id.server_id.fulldomain,
            '/home/backup/.ssh/keys/' +
            self.container_id.server_id.fulldomain, username='backup')
        backup.execute(['chmod', '-R', '700', '/home/backup/.ssh'],
                       username='backup')

        backup.execute(['rm', '-rf', directory], username='backup')
        backup.execute(['mkdir', '-p', directory], username='backup')

        backup.execute([
            'rsync', "-e 'ssh -o StrictHostKeyChecking=no'", '-ra',
            self.container_id.server_id.fulldomain + ':' + directory + '/',
            directory], username='backup')

        if backup.backup_method == 'simple':
            backup.execute([
                'mkdir', '-p', '/opt/backup/simple/' +
                self.repo_name + '/' + self.name], username='backup')
            backup.execute([
                'cp', '-R', directory + '/*',
                '/opt/backup/simple/' + self.repo_name + '/' + self.name],
                username='backup')
            backup.execute([
                'rm', '/opt/backup/simple/' + self.repo_name + '/latest'],
                username='backup')
            backup.execute([
                'ln', '-s',
                '/opt/backup/simple/' + self.repo_name + '/' + self.name,
                '/opt/backup/simple/' + self.repo_name + '/latest'],
                username='backup')

        if backup.backup_method == 'bup':
            backup.execute(['export BUP_DIR=/opt/backup/bup;',
                            'bup index ' + directory],
                           username='backup')
            backup.execute([
                'export BUP_DIR=/opt/backup/bup;',
                'bup save -n ' + self.repo_name + ' -d ' +
                str(int(self.now_epoch)) + ' --strip ' + directory],
                username='backup')

        backup.execute(['cat', directory + '/backup-date'])

        backup.execute(['rm', '-rf', directory + '*'], username='backup')

        # Should we delete the keys directory?
        # More security, but may cause concurrency problems
        # backup.execute(['rm', '/home/backup/.ssh/keys/*'], username='backup')

        container.execute(['rm', '-rf', directory + '*'])

        if self.base_fullname:
            container.execute([
                'rm', '-rf', '/base-backup/' + self.name], username='root')
        return

    @api.multi
    def purge(self):
        """
        Remove the save from the backup container.
        """
        self.backup_id.execute(['rm', '-rf', '/opt/backup/simple/' +
                                self.repo_name + '/' + self.name])
        flag = False
        if self.base_fullname:
            if self.search([('base_fullname', '=', self.repo_name)]) == self:
                flag = True
        else:
            if self.search([
                    ('container_fullname', '=', self.repo_name)]) == self:
                flag = True

        if flag:
            self.backup_id.execute(['rm', '-rf', '/opt/backup/simple/' +
                                    self.repo_name])
            self.backup_id.execute(['git', '--git-dir=/opt/backup/bup',
                                    'branch', '-D', self.repo_name])
        return

    @api.multi
    def restore_database(self, base):
        """

        :return:
        """
        base.purge_database()
        return

    @api.multi
    def restore_base(self, base):
        """
        Hook which can be called by submodules to execute commands after we
        restored a base.
        """
        return

    @api.multi
    def restore(self):
        """
        Restore a save to a container or a base. If container/service/base
        aren't specified, they will be created.
        """
        container_obj = self.env['clouder.container']
        base_obj = self.env['clouder.base']
        environment_obj = self.env['clouder.environment']
        server_obj = self.env['clouder.server']
        domain_obj = self.env['clouder.domain']
        application_obj = self.env['clouder.application']
        application_link_obj = self.env['clouder.application.link']
        image_obj = self.env['clouder.image']
        image_version_obj = self.env['clouder.image.version']

        environments = environment_obj.search([
            ('prefix', '=', self.computed_restore_to_environment)])
        if not environments:
                raise except_orm(
                    _('Error!'),
                    _("Couldn't find environment " +
                      self.computed_restore_to_environment +
                      ", aborting restoration."))
        apps = application_obj.search([('code', '=', self.container_app)])
        if not apps:
            raise except_orm(
                _('Error!'),
                _("Couldn't find application " + self.container_app +
                  ", aborting restoration."))

        if self.container_restore_to_suffix or not self.container_id:

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
                self.log(
                    "Warning, couldn't find the image version, using latest")
                # We do not want to force the upgrade if we had to use latest
                # upgrade = False
                versions = imgs[0].version_ids
                if not versions:
                    raise except_orm(
                        _('Error!'),
                        _("Couldn't find versions for image " +
                          self.container_img + ", aborting restoration."))
                img_versions = [versions[0]]

            containers = container_obj.search([
                ('environment_id.prefix', '=',
                 self.computed_restore_to_environment),
                ('suffix', '=', self.computed_container_restore_to_suffix),
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
                            link_vals['name'] = link_apps[0].id
                        else:
                            continue
                    del link_vals['code']
                    links.append((0, 0, link_vals))
                container_vals = {
                    'environment_id': environments[0].id,
                    'suffix': self.computed_container_restore_to_suffix,
                    'server_id': servers[0].id,
                    'application_id': apps[0].id,
                    'image_id': imgs[0].id,
                    'image_version_id': img_versions[0].id,
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

        if not self.base_fullname:

            if container.image_version_id != img_versions[0]:
                # if upgrade:
                container.image_version_id = img_versions[0]
                self = self.with_context(forcesave=False)
                self = self.with_context(nosave=True)

            self = self.with_context(
                save_comment='Before restore ' + self.name)
            container.save_exec(no_enqueue=True)

            self.restore_action(container)

            for volume in container.volume_ids:
                if volume.user:
                    container.execute(['chown', '-R',
                                       volume.user + ':' + volume.user,
                                       volume.name])

            container.start()

            container.deploy_links()
            res = container

        else:

            if self.base_restore_to_name or not self.base_fullname:
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
                        del link_vals['code']
                        links.append((0, 0, link_vals))
                    base_vals = {
                        'name': self.computed_base_restore_to_name,
                        'environment_id': environments[0].id,
                        'container_id': container.id,
                        'application_id': apps[0].id,
                        'domain_id': domains[0].id,
                        'title': self.base_title,
                        'admin_name': self.base_admin_name,
                        'admin_password': self.base_admin_password,
                        'admin_email': self.base_admin_email,
                        'poweruser_name': self.base_poweruser_name,
                        'poweruser_password': self.base_poweruser_password,
                        'poweruser_email': self.base_poweruser_email,
                        'build': self.base_build,
                        'test': self.base_test,
                        'lang': self.base_lang,
                        'autosave': self.base_autosave,
                        'option_ids': options,
                        'link_ids': links,
                        'backup_ids': [(6, 0, [self.backup_id.id])]
                    }
                    self = self.with_context(base_restoration=True)
                    base = self.env['clouder.base'].create(base_vals)
                    self = self.with_context(base_restoration=False)
                else:
                    self.log("A corresponding base was found")
                    base = bases[0]
            else:
                self.log("A base_id was linked in the save")
                base = self.base_id

            self = self.with_context(
                save_comment='Before restore ' + self.name)
            base.save_exec(no_enqueue=True)

            self.restore_action(base)

            self.restore_database(base)

            self.restore_base(base)

            base_obj.deploy_links()

            base.container_id.base_backup_container.execute(
                ['rm', '-rf', '/base-backup/restore-' + self.name],
                username='root')
            res = base
        self.write({'restore_to_environment_id': False,
                    'container_restore_to_suffix': False,
                    'container_restore_to_server_id': False,
                    'base_restore_to_name': False,
                    'base_restore_to_domain_id': False})

        return res

    @api.multi
    def restore_action(self, obj):
        """
        Execute the command on the backup container et destination container
        to get the save and restore it.

        :param obj: The object which will be restored.
        """

        container = obj
        if obj._name == 'clouder.base':
            container = obj.container_id.base_backup_container

        directory = '/tmp/clouder/restore-' + self.name

        backup = self.backup_id
        backup.send(self.home_directory + '/.ssh/config',
                    '/home/backup/.ssh/config', username='backup')
        backup.send(
            self.home_directory + '/.ssh/keys/' +
            container.server_id.fulldomain + '.pub',
            '/home/backup/.ssh/keys/' +
            container.server_id.fulldomain + '.pub',
            username='backup')
        backup.send(
            self.home_directory + '/.ssh/keys/' +
            container.server_id.fulldomain,
            '/home/backup/.ssh/keys/' + container.server_id.fulldomain,
            username='backup')
        backup.execute(['chmod', '-R', '700', '/home/backup/.ssh'],
                       username='backup')
        backup.execute(['rm', '-rf', directory + '*'], username='backup')
        backup.execute(['mkdir', '-p', directory], username='backup')

        if self.backup_id.backup_method == 'simple':
            backup.execute([
                'cp', '-R', '/opt/backup/simple/' + self.repo_name +
                '/' + self.name + '/*', directory], username='backup')

        if self.backup_id.backup_method == 'bup':
            backup.execute([
                'export BUP_DIR=/opt/backup/bup;',
                'bup restore -C ' + directory + ' ' + self.repo_name +
                '/' + self.now_bup], username='backup')
            backup.execute([
                'mv', directory + '/' + self.now_bup + '/*', directory],
                username='backup')
            backup.execute(['rm -rf', directory + '/' + self.now_bup],
                           username='backup')

        backup.execute([
            'rsync', "-e 'ssh -o StrictHostKeyChecking=no'", '-ra',
            directory + '/', container.server_id.fulldomain + ':' + directory],
            username='backup')
        backup.execute(['rm', '-rf', directory + '*'], username='backup')
        # backup.execute(['rm', '/home/backup/.ssh/keys/*'], username='backup')

        if not self.base_fullname:
            for volume in self.container_volumes_comma.split(','):
                container.execute([
                    'rm', '-rf', volume + '/*'], username='root')
        else:
            container.execute(
                ['rm', '-rf', '/base-backup/restore-' + self.name],
                username='root')

        container.server_id.execute(['ls', directory])
        container.server_id.execute(['cat', directory + '/backup-date'])
        container.server_id.execute(['rm', '-rf', directory + '/backup-date'])
        if not self.base_fullname:
            for item in \
                    container.server_id.execute(['ls', directory]).split('\n'):
                if item:
                    container.server_id.execute([
                        'docker', 'cp',
                        directory + '/' + item, container.name + ':/'])
        else:
            container.execute(['mkdir', '/base-backup/'], username='root')
            container.server_id.execute([
                'docker', 'cp', directory,
                container.name + ':/base-backup'])
            container.execute(['chmod', '-R', '777',
                               '/base-backup/restore-' + self.name],
                              username='root')
        container.server_id.execute(['rm', '-rf', directory + '*'])
