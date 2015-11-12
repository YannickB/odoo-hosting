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
import re


class ClouderApplicationType(models.Model):
    """
    Define the application.type object, mainly used to know which python code
    shall be used for an application.

    For example, when we deploy a base with an Odoo application with 'odoo' as
    the application type, clouder will check the module clouder_template_odoo
    to know the specific code to execute.
    """

    _name = 'clouder.application.type'

    name = fields.Char('Name', size=64, required=True)
    system_user = fields.Char('System User', size=64, required=True)
    localpath = fields.Char('Localpath', size=128)
    localpath_services = fields.Char('Localpath Services', size=128)
    option_ids = fields.One2many(
        'clouder.application.type.option', 'apptype_id', 'Options'
    )
    application_ids = fields.One2many(
        'clouder.application', 'type_id', 'Applications'
    )
    symlink = fields.Boolean('Use Symlink by default?')
    multiple_databases = fields.Char('Multiples databases?', size=128)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    @api.one
    @api.constrains('name', 'system_user')
    def _validate_data(self):
        """
        Check that the application type name does not contain any forbidden
        characters.
        """
        if not re.match("^[\w\d_]*$", self.name) \
                or not re.match("^[\w\d-]*$", self.system_user):
            raise except_orm(_('Data error!'), _(
                "Name and system_user can only contains letters, "
                "digits and -")
            )


class ClouderApplicationTypeOption(models.Model):
    """
    Define the application.type.option object, used to know which option can be
    assigned to application/container/service/base.
    """

    _name = 'clouder.application.type.option'

    apptype_id = fields.Many2one(
        'clouder.application.type',
        'Application Type', ondelete="cascade", required=True)
    name = fields.Char('Name', size=64, required=True)
    type = fields.Selection(
        [('application', 'Application'), ('container', 'Container'),
         ('service', 'Service'), ('base', 'Base')], 'Type', required=True)
    auto = fields.Boolean('Auto?')
    required = fields.Boolean('Required?')
    default = fields.Text('Default value')

    _sql_constraints = [
        ('name_uniq', 'unique(apptype_id,name)',
         'Options name must be unique per apptype!'),
    ]


class ClouderApplication(models.Model):
    """
    Define the application object, which represent the software which will be
    installed in container.
    """

    _name = 'clouder.application'

    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', size=20, required=True)
    type_id = fields.Many2one('clouder.application.type', 'Type',
                              required=True)
    current_version = fields.Char('Current version', size=64, required=True)
    next_server_id = fields.Many2one('clouder.server', 'Next server')
    default_image_id = fields.Many2one('clouder.image', 'Default Image',
                                       required=True)
    admin_name = fields.Char('Admin name', size=64)
    admin_email = fields.Char('Admin email', size=64)
    archive_id = fields.Many2one('clouder.container', 'Archive')
    option_ids = fields.One2many('clouder.application.option',
                                 'application_id', 'Options')
    link_ids = fields.One2many('clouder.application.link', 'application_id',
                               'Links')
    link_target_ids = fields.One2many('clouder.application.link', 'name',
                                      'Links Targets')
    parent_id = fields.Many2one('clouder.application', 'Parent')
    required = fields.Boolean('Required?')
    sequence = fields.Integer('Sequence')
    child_ids = fields.One2many('clouder.application', 'parent_id', 'Childs')
    version_ids = fields.One2many('clouder.application.version',
                                  'application_id', 'Versions')
    buildfile = fields.Text('Build File')
    container_ids = fields.One2many('clouder.container', 'application_id',
                                    'Containers')
    container_backup_ids = fields.Many2many(
        'clouder.container', 'clouder_application_container_backup_rel',
        'application_id', 'backup_id', 'Backups Containers')
    container_time_between_save = fields.Integer(
        'Minutes between each container save', required=True, default=9999)
    container_saverepo_change = fields.Integer(
        'Days before container saverepo change', required=True, default=30)
    container_saverepo_expiration = fields.Integer(
        'Days before container saverepo expiration', required=True, default=90)
    container_save_expiration = fields.Integer(
        'Days before container save expiration', required=True, default=5)
    base_backup_ids = fields.Many2many(
        'clouder.container', 'clouder_application_base_backup_rel',
        'application_id', 'backup_id', 'Backups Bases')
    base_time_between_save = fields.Integer('Minutes between each base save',
                                            required=True, default=9999)
    base_saverepo_change = fields.Integer('Days before base saverepo change',
                                          required=True, default=30)
    base_saverepo_expiration = fields.Integer(
        'Days before base saverepo expiration', required=True, default=90)
    base_save_expiration = fields.Integer('Days before base save expiration',
                                          required=True, default=5)
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.env['clouder.model'].user_partner)

    @property
    def full_archivepath(self):
        """
        Property returning the full path to the archive
        in the archive container
        """
        return self.env['clouder.model'].archive_path + '/' \
            + self.type_id.name + '-' + self.code

    @property
    def full_hostpath(self):
        """
        Property returning the full path to the archive
        in the hosting system.
        """
        return self.env['clouder.model'].services_hostpath + '/' \
            + self.type_id.name + '-' + self.code

    @property
    def full_localpath(self):
        """
        Property returning the full path to the instance
        in the destination container
        """
        return self.type_id.localpath and self.type_id.localpath + '/' \
            + self.type_id.name + '-' + self.code or ''

    @property
    def computed_version(self):
        """
        Property returning the name of the application version
        with the current date.
        """
        return self.current_version + '.' \
            + datetime.now().strftime('%Y%m%d.%H%M%S')

    @property
    def options(self):
        """
        Property returning a dictionary containing the value of all options
        for this application, even is they are not defined here.
        """
        options = {}
        for option in self.type_id.option_ids:
            if option.type == 'application':
                options[option.name] = {'id': option.id, 'name': option.name,
                                        'value': option.default}
        for option in self.option_ids:
            options[option.name.name] = {'id': option.id,
                                         'name': option.name.name,
                                         'value': option.value}
        return options

    _sql_constraints = [
        ('code_uniq', 'unique(parent_id, code)', 'Code must be unique!'),
    ]

    _order = 'code, sequence'

    @api.one
    @api.constrains('code', 'admin_name', 'admin_email')
    def _validate_data(self):
        """
        Check that the application name does not contain any forbidden
        characters.
        """

        if not re.match("^[\w\d-]*$", self.code) or len(self.code) > 20:
            raise except_orm(_('Data error!'), _(
                "Code can only contains letters, digits and "
                "- and shall be less than 20 characters"))
        if self.admin_name and not re.match("^[\w\d_]*$", self.admin_name):
            raise except_orm(_('Data error!'), _(
                "Admin name can only contains letters, digits and underscore"))
        if self.admin_email \
                and not re.match("^[\w\d_@.-]*$", self.admin_email):
            raise except_orm(_('Data error!'), _(
                "Admin email can only contains letters, "
                "digits, underscore, - and @"))

    @api.multi
    @api.onchange('type_id')
    def onchange_type_id(self):
        """
        Update the options when we change the type_id field.
        """
        if self.type_id:
            options = []
            for type_option in self.type_id.option_ids:
                if type_option.type == 'application' and type_option.auto:
                    test = False
                    for option in self.option_ids:
                        if option.name == type_option:
                            test = True
                    if not test:
                        options.append((0, 0,
                                        {'name': type_option,
                                         'value': type_option.default}))
            self.option_ids = options

    @api.multi
    def write(self, vals):
        """
        Override the write method to prevent change of the application code.

        :param vals: The values to update
        """
        if 'code' in vals and vals['code'] != self.code:
            raise except_orm(_('Data error!'), _(
                "It's too dangerous to modify the application code!"))
        return super(ClouderApplication, self).write(vals)

    @api.multi
    def get_current_version(self):
        """
        Hook which can be used to return the version of the application.
        """
        return False

    @api.multi
    def build(self):
        """
        Method to generate a new application version.
        """
        if not self.archive_id:
            raise except_orm(_('Data error!'), _(
                "You need to specify the archive where "
                "the version must be stored."))

        current_version = self.get_current_version()
        if current_version:
            self.write({'current_version': current_version})
        current_version = current_version or self.current_version
        now = datetime.now()
        version = current_version + '.' + now.strftime('%Y%m%d.%H%M%S')
        self.env['clouder.application.version'].create(
            {'application_id': self.id, 'name': version,
             'archive_id': self.archive_id and self.archive_id.id})


class ClouderApplicationOption(models.Model):
    """
    Define the application.option object, used to define custom values specific
    to an application.
    """

    _name = 'clouder.application.option'

    application_id = fields.Many2one('clouder.application', 'Application',
                                     ondelete="cascade", required=True)
    name = fields.Many2one('clouder.application.type.option', 'Option',
                           required=True)
    value = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(application_id,name)',
         'Option name must be unique per application!'),
    ]


class ClouderApplicationVersion(models.Model):
    """
    Define the application.version object, which represent each build of
    the application.
    """

    _name = 'clouder.application.version'
    _inherit = ['clouder.model']

    name = fields.Char('Name', size=64, required=True)
    application_id = fields.Many2one('clouder.application', 'Application',
                                     required=True)
    archive_id = fields.Many2one('clouder.container', 'Archive', required=True)
    service_ids = fields.One2many('clouder.service', 'application_version_id',
                                  'Services')

    @property
    def fullname(self):
        """
        Property returning the full name of the application version.
        """
        return self.application_id.code + '_' + self.name

    @property
    def full_archivepath(self):
        """
        Property returning the full path to the archive version
        in the archive container.
        """
        return self.application_id.full_archivepath + '/' + self.name

    @property
    def full_archivepath_targz(self):
        """
        Property returning the full path to the tar.gz of the archive version
        in the archive container.
        """
        return self.application_id.full_archivepath \
            + '/' + self.name + '.tar.gz'

    @property
    def full_hostpath(self):
        """
        Property returning the full path to the archive version
        in the hosting system.
        """
        return self.application_id.full_hostpath + '/' + self.name

    @property
    def full_localpath(self):
        """
        Property returning the full path to the archive version
        in the destination container.
        """
        return self.application_id.full_localpath + '/' + self.name

    _sql_constraints = [
        ('name_app_uniq', 'unique (name,application_id)',
         'The name of the version must be unique per application !')
    ]

    @api.one
    @api.constrains('name')
    def _validate_data(self):
        """
        Check that the application version name does not contain any forbidden
        characters.
        """
        if not re.match("^[\w\d_.]*$", self.name):
            raise except_orm(_('Data error!'), _(
                "Application version can only contains letters, "
                "digits and underscore and dot"))

    _order = 'create_date desc'

    @api.one
    def unlink(self):
        """
        Override unlink method to prevent application version unlink if
        some services are linked to it.
        """
        if self.service_ids:
            raise except_orm(_('Inherit error!'), _(
                "A service is linked to this application version, "
                "you can't delete it!"))
        return super(ClouderApplicationVersion, self).unlink()

    @api.multi
    def build_application(self):
        """
        Hook which can be used to call command specific to an application
        to build an application.
        """
        return

    @api.multi
    def deploy(self):
        """
        Build the application archive and store it in the archive container.
        """
        ssh = self.connect(self.archive_id.fullname)
        self.execute(ssh, ['mkdir', self.application_id.full_archivepath])
        self.execute(ssh, ['rm', '-rf', self.full_archivepath])
        self.execute(ssh, ['mkdir', self.full_archivepath])
        self.build_application()
        self.execute(ssh, ['echo "' + self.name + '" >> '
                           + self.full_archivepath + '/VERSION.txt'])
        self.execute(ssh, ['tar', 'czf', self.full_archivepath_targz, '-C',
                           self.application_id.full_archivepath + '/'
                           + self.name, '.'])
        ssh.close()

    @api.multi
    def purge(self):
        """
        Remove the application archive in the archive container.
        """
        ssh = self.connect(self.archive_id.fullname)
        self.execute(ssh, ['rm', '-rf', self.full_archivepath])
        self.execute(ssh, ['rm', self.full_archivepath_targz])
        ssh.close()


class ClouderApplicationLink(models.Model):
    """
    Define the application.link object, used to know which others applications
    can be link to this application.
    """

    _name = 'clouder.application.link'

    application_id = fields.Many2one('clouder.application', 'Application',
                                     ondelete="cascade", required=True)
    name = fields.Many2one('clouder.application', 'Application', required=True)
    required = fields.Boolean('Required?')
    auto = fields.Boolean('Auto?')
    make_link = fields.Boolean('Make docker link?')
    container = fields.Boolean('Container?')
    service = fields.Boolean('Service?')
    base = fields.Boolean('Base?')
    next = fields.Many2one('clouder.container', 'Next')

    _sql_constraints = [
        ('name_uniq', 'unique(application_id,name)',
         'Links must be unique per application!'),
    ]