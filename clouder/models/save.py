# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


from openerp import models, fields, api

from datetime import datetime
import ast
import os

import logging

_logger = logging.getLogger(__name__)


class ClouderSave(models.Model):
    """
    Define the save.save object, which represent the saves of services/bases.
    """

    _name = 'clouder.save'
    _inherit = ['clouder.model']

    name = fields.Char('Name', required=True)
    backup_id = fields.Many2one(
        'clouder.service', 'Backup Server', required=True)
    date_expiration = fields.Date('Expiration Date')
    comment = fields.Text('Comment')
    now_bup = fields.Char('Now bup')
    environment = fields.Char(
        'Environment', readonly=True)
    service_id = fields.Many2one('clouder.service', 'Service')
    service_fullname = fields.Char('Service Fullname')
    service_app = fields.Char('Application')
    service_img = fields.Char('Image')
    service_img_version = fields.Char('Image Version')
    service_ports = fields.Text('Ports')
    service_volumes = fields.Text('Volumes')
    service_volumes_comma = fields.Text('Volumes comma')
    service_options = fields.Text('Service Options')
    service_links = fields.Text('Service Links')
    base_id = fields.Many2one('clouder.base', 'Base')
    base_fullname = fields.Char('Base Fullname')
    base_title = fields.Char('Title')
    base_service_suffix = fields.Char('Service Name')
    base_service_server = fields.Char('Server')
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
    service_suffix = fields.Char(
        'Service Suffix', readonly=True)
    service_server = fields.Char(
        'Service Server',
        type='char', readonly=True)
    restore_to_environment_id = fields.Many2one(
        'clouder.environment', 'Restore to (Environment)')
    service_restore_to_suffix = fields.Char('Restore to (Suffix)')
    service_restore_to_server_id = fields.Many2one(
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
    def computed_service_restore_to_suffix(self):
        """
        Property returning the service suffix which will be restored.
        """
        return self.service_restore_to_suffix or self.base_service_suffix \
            or self.repo_id.service_suffix

    @property
    def computed_service_restore_to_server(self):
        """
        Property returning the service server which will be restored.
        """
        return self.service_restore_to_server_id.fulldomain \
            or self.base_service_server or self.repo_id.service_server

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
        repo_name = self.service_fullname
        if self.base_fullname:
            repo_name = self.base_fullname
        return repo_name

    _order = 'create_date desc'

    @api.multi
    def create(self, vals):
        """
        Override create method to add the data in service and base in the
        save record, so we can restore it if the service/service/base are
        deleted.

        :param vals: The values we need to create the record.
        """
        if 'service_id' in vals:
            service = self.env['clouder.service'] \
                .browse(vals['service_id'])

            service_ports = {}
            for port in service.port_ids:
                service_ports[port.name] = {
                    'name': port.name, 'localport': port.localport,
                    'expose': port.expose, 'udp': port.udp}

            service_volumes = {}
            for volume in service.volume_ids:
                service_volumes[volume.id] = {
                    'name': volume.name, 'hostpath': volume.hostpath,
                    'user': volume.user, 'readonly': volume.readonly,
                    'nosave': volume.nosave}

            service_links = {}
            for link in service.link_ids:
                service_links[link.name.code] = {
                    'name': link.name.id,
                    'code': link.name.code,
                    'target': link.target and link.target.id or False
                }

            vals.update({
                'environment': service.environment_id.prefix,
                'service_fullname': service.fullname,
                'service_suffix': service.suffix,
                'service_server': service.server_id.fulldomain,
                'service_volumes_comma': service.volumes_save,
                'service_app': service.application_id.code,
                'service_img': service.image_id.name,
                'service_img_version': service.image_version_id.name,
                'service_ports': str(service_ports),
                'service_volumes': str(service_volumes),
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
                    'target': link.target and link.target.id or False
                }

            vals.update({
                'environment': base.environment_id.prefix,
                'base_fullname': base.fullname,
                'base_name': base.name,
                'base_domain': base.domain_id.name,
                'base_title': base.title,
                'base_service_environment':
                    base.service_id.environment_id.prefix,
                'base_service_suffix': base.service_id.suffix,
                'base_service_server':
                base.service_id.server_id.fulldomain,
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
        Build the save and move it into the backup service.
        """

        super(ClouderSave, self).deploy()

        self.ensure_one()

        self.log('Saving "%s"' % self.name)
        self.log('Comment: "%s"' % self.comment)

        service = 'exec' in self.service_id.childs \
                  and self.service_id.childs['exec'] or self.service_id
        backup_dir = os.path.join(self.BACKUP_BASE_DIR, self.name)

        if self.base_fullname:
            service = service.base_backup_service
            service.execute([
                'mkdir', '-p', backup_dir,
            ],
                username='root',
            )

            service.execute([
                'chmod', '-R', '777', backup_dir,
            ],
                username='root',
            )
            self.save_database()
            self.deploy_base()

        directory = self.get_directory_clouder(self.name)
        service.server_id.execute([
            'rm', '-rf', os.path.join(directory, '*'),
        ])
        service.server_id.execute(['mkdir', directory])

        if self.base_fullname:
            service.server_id.execute([
                'docker', 'cp',
                '%s:%s' % (service.pod, backup_dir),
                self.get_directory_clouder(),
            ])
        else:
            for volume in self.service_volumes_comma.split(','):
                service.server_id.execute([
                    'mkdir', '-p', os.path.join(directory, volume),
                ])
                service.server_id.execute([
                    'docker', 'cp', '%s:%s' % (service.pod, volume),
                    os.path.join(directory, os.path.split(volume)[0]),
                ])

        service.server_id.execute([
            'echo "%s" > "%s"' % (
                self.now_date, os.path.join(directory, self.BACKUP_DATE_FILE),
            ),
        ])
        service.server_id.execute([
            'chmod', '-R', '777', os.path.join(directory, '*'),
        ])

        backup = self.backup_id
        if self.base_fullname:
            name = self.base_id.fullname_
        else:
            name = self.service_id.fullname

        backup.execute([
            'rm', '-rf', os.path.join(
                self.BACKUP_DATA_DIR, 'list', name,
            ),
        ],
            username='backup',
        )
        backup.execute([
            'mkdir', '-p', os.path.join(
                self.BACKUP_DATA_DIR, 'list', name,
            ),
        ],
            username='backup',
        )
        backup.execute([
            'echo "%s" > "%s"' % (
                self.repo_name, os.path.join(
                    self.BACKUP_DATA_DIR, 'list', name, 'repo',
                )
            )
        ],
            username='backup',
        )

        backup.send(
            os.path.join(self.home_directory, '.ssh', 'config'),
            os.path.join(self.BACKUP_HOME_DIR, '.ssh', 'config'),
            username='backup',
        )
        backup.send(
            os.path.join(self.home_directory, '.ssh', 'keys',
                         '%s.pub' % self.service_id.server_id.fulldomain),
            os.path.join(self.BACKUP_HOME_DIR, '.ssh', 'keys',
                         '%s.pub' % self.service_id.server_id.fulldomain),
            username='backup',
        )
        backup.send(
            os.path.join(self.home_directory, '.ssh', 'keys',
                         self.service_id.server_id.fulldomain),
            os.path.join(self.BACKUP_HOME_DIR, '.ssh', 'keys',
                         self.service_id.server_id.fulldomain),
            username='backup',
        )
        backup.execute([
            'chmod', '-R', '700', os.path.join(self.BACKUP_HOME_DIR, '.ssh'),
        ],
            username='backup',
        )

        backup.execute(['rm', '-rf', directory], username='backup')
        backup.execute(['mkdir', '-p', directory], username='backup')

        backup.execute([
            'rsync', "-e 'ssh -o StrictHostKeyChecking=no'", '-ra',
            '%s:%s/' % (self.service_id.server_id.fulldomain, directory),
            directory,
        ],
            username='backup',
        )

        if backup.backup_method == 'simple':
            backup_dir = os.path.join(
                self.BACKUP_DATA_DIR, 'simple', self.repo_name,
            )
            backup.execute(['mkdir', '-p', backup_dir], username='backup')
            backup.execute([
                'cp', '-R',
                os.path.join(directory, '*'),
                os.path.join(backup_dir, self.name),
            ],
                username='backup',
            )
            backup.execute([
                'rm', os.path.join(backup_dir, 'latest')
            ],
                username='backup',
            )
            backup.execute([
                'ln', '-s',
                os.path.join(backup_dir, self.name),
                os.path.join(backup_dir, 'latest'),
            ],
                username='backup',
            )

        if backup.backup_method == 'bup':
            backup_dir = os.path.join(self.BACKUP_DATA_DIR, 'bup')
            backup.execute([
                'export BUP_DIR="%s";' % backup_dir,
                'bup index "%s"' % directory,
            ],
                username='backup',
            )
            backup.execute([
                'export BUP_DIR="%s";' % backup_dir,
                'bup save -n "%s" -d %d --strip "%s"' % (
                    self.repo_name, int(self.now_epoch), directory,
                )
            ],
                username='backup',
            )

        backup.execute([
            'cat', os.path.join(directory, self.BACKUP_DATE_FILE),
        ])

        delete_dir = ['rm', '-rf', os.path.join(directory, '*')]
        backup.execute(delete_dir, username='backup')
        service.execute(delete_dir)

        # Should we delete the keys directory?
        # More security, but may cause concurrency problems
        # backup.execute(['rm', '/home/backup/.ssh/keys/*'], username='backup')

        if self.base_fullname:
            service.execute([
                'rm', '-rf', os.path.join(self.BACKUP_BASE_DIR, self.name),
            ],
                username='root',
            )
        return

    @api.multi
    def purge(self):
        """
        Remove the save from the backup service.
        """

        backup_root = os.path.join(
            self.BACKUP_DATA_DIR, 'simple', self.repo_name,
        )
        self.backup_id.execute([
            'rm', '-rf',
            os.path.join(backup_root, self.name),
        ])

        if self.base_fullname:
            search_field = 'base_fullname'
        else:
            search_field = 'service_fullname'

        if self.search([(search_field, '=', self.repo_name)]) == self:
            self.backup_id.execute(['rm', '-rf', backup_root])
            self.backup_id.execute([
                'git',
                '--git-dir="%s"' % os.path.join(self.BACKUP_DATA_DIR, 'bup'),
                'branch', '-D', self.repo_name,
            ])
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
        Restore a save to a service or a base. If service/service/base
        aren't specified, they will be created.
        """
        service_obj = self.env['clouder.service']
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
                self.raise_error(
                    'Could not find environment "%s". Aborting restoration.',
                    self.computed_restore_to_environment,
                )
        apps = application_obj.search([('code', '=', self.service_app)])
        if not apps:
            self.raise_error(
                'Could not find application "%s". Aborting restoration.',
                self.service_app,
            )

        if self.service_restore_to_suffix or not self.service_id:

            imgs = image_obj.search([('name', '=', self.service_img)])
            if not imgs:
                self.raise_error(
                    'Could not find the image "%s". Aborting restoration.',
                    self.service_img,
                )

            img_versions = image_version_obj.search(
                [('name', '=', self.service_img_version)])
            # upgrade = True
            if not img_versions:
                self.log(
                    "Warning, could not find the image version, using latest")
                # We do not want to force the upgrade if we had to use latest
                # upgrade = False
                versions = imgs[0].version_ids
                if not versions:
                    self.raise_error(
                        'Could not find versions for image "%s". '
                        'Aborting restoration.',
                        self.service_img,
                    )
                img_versions = [versions[0]]

            services = service_obj.search([
                ('environment_id.prefix', '=',
                 self.computed_restore_to_environment),
                ('suffix', '=', self.computed_service_restore_to_suffix),
                ('server_id.name', '=',
                 self.computed_service_restore_to_server)
            ])

            if not services:
                self.log("Can't find any corresponding service, "
                         "creating a new one")
                servers = server_obj.search([
                    ('name', '=', self.computed_service_restore_to_server)])
                if not servers:
                    self.raise_error(
                        'Could not find server "%s". Aborting restoration.',
                        self.computed_service_restore_to_server,
                    )

                ports = []
                for port, port_vals \
                        in ast.literal_eval(self.service_ports).iteritems():
                    ports.append((0, 0, port_vals))
                volumes = []
                for volume, volume_vals in \
                        ast.literal_eval(self.service_volumes).iteritems():
                    volumes.append((0, 0, volume_vals))
                options = []
                for option, option_vals in \
                        ast.literal_eval(self.service_options).iteritems():
                    del option_vals['id']
                    options.append((0, 0, option_vals))
                links = []
                for link, link_vals in ast.literal_eval(
                        self.service_links).iteritems():
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
                service_vals = {
                    'environment_id': environments[0].id,
                    'suffix': self.computed_service_restore_to_suffix,
                    'server_id': servers[0].id,
                    'application_id': apps[0].id,
                    'image_id': imgs[0].id,
                    'image_version_id': img_versions[0].id,
                    'port_ids': ports,
                    'volume_ids': volumes,
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

        if not self.base_fullname:

            if service.image_version_id != img_versions[0]:
                # if upgrade:
                service.image_version_id = img_versions[0]
                self = self.with_context(forcesave=False)
                self = self.with_context(nosave=True)

            self = self.with_context(
                save_comment='Before restore ' + self.name)
            service.save_exec(no_enqueue=True)

            self.restore_action(service)

            for volume in service.volume_ids:
                if volume.user:
                    service.execute(['chown', '-R',
                                     volume.user + ':' + volume.user,
                                     volume.name])

            service.start()

            service.deploy_links()
            res = service

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
                        self.raise_error(
                            'Could not find domain "%s". '
                            'Aborting restoration.',
                            self.computed_base_restore_to_domain,
                        )
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
                        'service_id': service.id,
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

            base.service_id.base_backup_service.execute([
                'rm', '-rf', os.path.join(
                    self.BACKUP_BASE_DIR, 'restore-%s' % self.name,
                )
            ],
                username='root',
            )
            res = base
        self.write({'restore_to_environment_id': False,
                    'service_restore_to_suffix': False,
                    'service_restore_to_server_id': False,
                    'base_restore_to_name': False,
                    'base_restore_to_domain_id': False})

        return res

    @api.multi
    def restore_action(self, obj):
        """
        Execute the command on the backup service et destination service
        to get the save and restore it.

        :param obj: The object which will be restored.
        """

        service = obj
        if obj._name == 'clouder.base':
            service = obj.service_id.base_backup_service

        directory = self.get_directory_clouder('restore-%s' % self.name)

        backup = self.backup_id
        backup.send(
            os.path.join(self.home_directory, '.ssh', 'config'),
            os.path.join(self.BACKUP_HOME_DIR, '.ssh', 'config'),
            username='backup',
        )
        backup.send(
            os.path.join(self.home_directory, '.ssh', 'keys',
                         '%s.pub' % service.server_id.fulldomain),
            os.path.join(self.BACKUP_HOME_DIR, '.ssh', 'keys',
                         '%s.pub' % service.server_id.fulldomain),
            username='backup',
        )
        backup.send(
            os.path.join(self.home_directory, '.ssh', 'keys',
                         service.server_id.fulldomain),
            os.path.join(self.BACKUP_HOME_DIR, '.ssh', 'keys',
                         service.server_id.fulldomain),
            username='backup',
        )
        backup.execute([
            'chmod', '-R', '700', os.path.join(self.BACKUP_HOME_DIR, '.ssh'),
        ],
            username='backup',
        )
        backup.execute(
            ['rm', '-rf', os.path.join(directory, '*')],
            username='backup',
        )
        backup.execute(['mkdir', '-p', directory], username='backup')

        if self.backup_id.backup_method == 'simple':
            backup.execute([
                'cp', '-R',
                os.path.join(self.BACKUP_DATA_DIR, 'simple', self.repo_name,
                             self.name, '*'),
                directory,
            ],
                username='backup',
            )

        if self.backup_id.backup_method == 'bup':
            backup.execute([
                'export BUP_DIR="%s";' % os.path.join(
                    self.BACKUP_DATA_DIR, 'bup',
                ),
                'bup restore -C "%s" "%s"' % (
                    directory, os.path.join(self.repo_name, self.now_bup),
                )
            ],
                username='backup',
            )
            backup.execute([
                'mv', os.path.join(directory, self.now_bup, '*'), directory,
            ],
                username='backup',
            )
            backup.execute(['rm -rf', os.path.join(directory, self.now_bup)],
                           username='backup')

        backup.execute([
            'rsync', "-e 'ssh -o StrictHostKeyChecking=no'", '-ra',
            directory, '%s:%s' % (service.server_id.fulldomain, directory),
        ],
            username='backup',
        )
        backup.execute(
            ['rm', '-rf', os.path.join(directory, '*')],
            username='backup',
        )
        # backup.execute(['rm', '/home/backup/.ssh/keys/*'], username='backup')

        if not self.base_fullname:
            for volume in self.service_volumes_comma.split(','):
                service.execute([
                    'rm', '-rf', os.path.join(volume, '*'),
                ],
                    username='root',
                )
        else:
            service.execute([
                'rm', '-rf',
                os.path.join(self.BACKUP_BASE_DIR, 'restore-%s' % self.name),
            ],
                username='root',
            )

        service.server_id.execute(['ls', directory])
        service.server_id.execute([
            'cat', os.path.join(directory, self.BACKUP_DATE_FILE),
        ])
        service.server_id.execute([
            'rm', '-rf', os.path.join(directory, self.BACKUP_DATE_FILE),
        ])
        if not self.base_fullname:
            for item in \
                    service.server_id.execute(['ls', directory]).split('\n'):
                if item:
                    service.server_id.execute([
                        'docker', 'cp',
                        os.path.join(directory, item),
                        '%s:/' % service.name,
                    ])
        else:
            service.execute(
                ['mkdir', self.BACKUP_BASE_DIR],
                username='root',
            )
            service.server_id.execute([
                'docker', 'cp', directory,
                '%s:/base-backup' % service.name,
            ])
            service.execute([
                'chmod', '-R', '777',
                os.path.join(self.BACKUP_BASE_DIR, 'restore-%s' % self.name),
            ],
                username='root',
            )
        service.server_id.execute(
            ['rm', '-rf', os.path.join(directory, '*')],
        )
