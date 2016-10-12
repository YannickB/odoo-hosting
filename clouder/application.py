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

import model


class ClouderApplicationTag(models.Model):

    _name = 'clouder.application.tag'

    name = fields.Char('Name', required=True)
    application_ids = fields.Many2many(
        'clouder.application', 'clouder_application_tag_rel',
        'tag_id', 'application_id', 'Applications')


class ClouderApplicationType(models.Model):
    """
    Define the application.type object, mainly used to know which python code
    shall be used for an application.

    For example, when we deploy a base with an Odoo application with 'odoo' as
    the application type, clouder will check the module clouder_template_odoo
    to know the specific code to execute.
    """

    _name = 'clouder.application.type'

    name = fields.Char('Name', required=True)
    system_user = fields.Char('System User', required=True)
    localpath = fields.Char('Localpath')
    localpath_services = fields.Char('Localpath Services')
    option_ids = fields.One2many(
        'clouder.application.type.option', 'application_type_id', 'Options'
    )
    application_ids = fields.One2many(
        'clouder.application', 'type_id', 'Applications'
    )
    symlink = fields.Boolean('Use Symlink by default?')
    multiple_databases = fields.Char('Multiples databases?')
    tag_ids = fields.Many2many(
        'clouder.application.tag', 'clouder_application_type_tag_rel',
        'type_id', 'tag_id', 'Tags')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    _order = 'name'

    @api.one
    @api.constrains('name', 'system_user')
    def _check_forbidden_chars_name_sys_user(self):
        """
        Check that the application type name does not contain any forbidden
        characters.
        """
        if not re.match("^[\w\d-]*$", self.name) \
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

    application_type_id = fields.Many2one(
        'clouder.application.type',
        'Application Type', ondelete="cascade", required=True)
    name = fields.Char('Name', required=True)
    type = fields.Selection(
        [('application', 'Application'), ('container', 'Container'),
         ('service', 'Service'), ('base', 'Base')], 'Type', required=True)
    application_code = fields.Char('Application Code')
    tag_ids = fields.Many2many(
        'clouder.application.tag', 'clouder_application_type_option_tag_rel',
        'option_id', 'tag_id', 'Tags')
    auto = fields.Boolean('Auto?')
    required = fields.Boolean('Required?')
    default = fields.Text('Default value')

    _sql_constraints = [
        ('name_uniq', 'unique(application_type_id,name)',
         'Options name must be unique per apptype!'),
    ]

    @api.multi
    def generate_default(self):
        res = ''
        if self.name == 'db_password':
            res = model.generate_random_password(20)
        if self.name == 'secret':
            res = model.generate_random_password(50)
        if self.name == 'ssh_privatekey':
            res = self.env['clouder.server']._default_private_key()
        if self.name == 'ssh_publickey':
            res = self.env['clouder.server']._default_public_key()
        return res

    @property
    def get_default(self):
        if self.default:
            return self.default
        else:
            return self.generate_default()


class ClouderApplicationTemplate(models.Model):
    """
    """

    _name = 'clouder.application.template'

    name = fields.Char('Name', required=True)
    link_ids = fields.One2many('clouder.application.link', 'template_id',
                               'Links')


class ClouderApplication(models.Model):
    """
    Define the application object, which represent the software which will be
    installed in container.
    """

    _name = 'clouder.application'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    type_id = fields.Many2one('clouder.application.type', 'Type',
                              required=True)
    template_ids = fields.Many2many(
        'clouder.application.template', 'clouder_application_template_rel',
        'application_id', 'template_id', 'Templates')
    current_version = fields.Char('Current version')
    next_server_id = fields.Many2one('clouder.server', 'Next server')
    default_image_id = fields.Many2one('clouder.image', 'Default Image',
                                       required=False)
    next_image_version_id = fields.Many2one(
        'clouder.image.version', 'Next Image Version')
    base = fields.Boolean('Can have base?')
    tag_ids = fields.Many2many(
        'clouder.application.tag', 'clouder_application_tag_rel',
        'application_id', 'tag_id', 'Tags')
    next_container_id = fields.Many2one('clouder.container', 'Next container')
    admin_name = fields.Char('Admin name')
    admin_email = fields.Char('Admin email')
    archive_id = fields.Many2one('clouder.container', 'Archive')
    option_ids = fields.One2many('clouder.application.option',
                                 'application_id', 'Options')
    link_ids = fields.One2many('clouder.application.link', 'application_id',
                               'Links')
    link_target_ids = fields.One2many('clouder.application.link', 'name',
                                      'Links Targets')
    metadata_ids = fields.One2many(
        'clouder.application.metadata', 'application_id', 'Metadata')
    required = fields.Boolean('Required?')
    sequence = fields.Integer('Sequence')
    child_ids = fields.Many2many(
        'clouder.application', 'clouder_application_parent_child_rel',
        'parent_id', 'child_id', 'Childs')
    container_ids = fields.One2many('clouder.container', 'application_id',
                                    'Containers')
    update_strategy = fields.Selection([
        ('never', 'Never'), ('manual', 'Manual'), ('auto', 'Automatic')],
        string='Container Update Strategy', required=True, default='never')
    update_bases = fields.Boolean('Update bases?')
    autosave = fields.Boolean('Save?')
    container_backup_ids = fields.Many2many(
        'clouder.container', 'clouder_application_container_backup_rel',
        'application_id', 'backup_id', 'Backups Containers')
    container_time_between_save = fields.Integer(
        'Minutes between each container save', required=True, default=9999)
    container_save_expiration = fields.Integer(
        'Days before container save expiration', required=True, default=5)
    base_backup_ids = fields.Many2many(
        'clouder.container', 'clouder_application_base_backup_rel',
        'application_id', 'backup_id', 'Backups Bases')
    base_time_between_save = fields.Integer('Minutes between each base save',
                                            required=True, default=9999)
    base_save_expiration = fields.Integer('Days before base save expiration',
                                          required=True, default=5)
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.env['clouder.model'].user_partner)

    @property
    def fullcode(self):
        fullcode = self.code
        return fullcode

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

    @property
    def links(self):
        """
        """
        links = {}
        for child in self.child_ids:
            for code, link in child.links.iteritems():
                links[code] = link
        for link in self.link_ids:
            links[link.name.code] = link
        return links

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    _order = 'sequence, code'

    @api.one
    @api.constrains('code', 'admin_name', 'admin_email')
    def _check_forbidden_chars_credentials_code(self):
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

    @api.one
    @api.constrains('default_image_id', 'child_ids')
    def _check_image(self):
        """
        """
        if not self.default_image_id and not self.child_ids:
            raise self.raise_error('You need to specify the image!')

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
    def check_tags(self, needed_tags):
        tags = {}
        for tag in self.type_id.tag_ids:
            tags[tag.name] = tag.name
        for tag in self.tag_ids:
            tags[tag.name] = tag.name

        for needed_tag in needed_tags:
            if needed_tag not in tags:
                return False
        return True

    @api.model
    def create(self, vals):
        """
        """
        res = super(ClouderApplication, self).create(vals)
        if 'template_ids' in vals:
            for template in res.template_ids:
                for link in self.env['clouder.application.link'].search([
                        ('template_id', '=', template.id)]):
                    link.reset_template(records=[res])
        return res

    @api.multi
    def write(self, vals):
        """
        Override the write method to prevent change of the application code.

        :param vals: The values to update
        """
        if 'code' in vals and vals['code'] != self.code:
            raise except_orm(_('Data error!'), _(
                "It's too dangerous to modify the application code!"))
        res = super(ClouderApplication, self).write(vals)
        if 'template_id' in vals:
            self = self.browse(self.id)
            for template in self.template_ids:
                for link in self.env['clouder.application.link'].search([
                        ('template_id', '=', template.id)]):
                    link.reset_template(records=[self])
        return res


class ClouderApplicationOption(models.Model):
    """
    Define the application.option object, used to define custom values specific
    to an application.
    """

    _name = 'clouder.application.option'

    application_id = fields.Many2one('clouder.application', 'Application',
                                     ondelete="cascade", required=False)
    template_id = fields.Many2one(
        'clouder.application.template', 'Template', ondelete="cascade")
    name = fields.Many2one('clouder.application.type.option', 'Option',
                           required=True)
    value = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(application_id,template_id,name)',
         'Option name must be unique per application!'),
    ]


class ClouderApplicationLink(models.Model):
    """
    Define the application.link object, used to know which others applications
    can be link to this application.
    """

    _name = 'clouder.application.link'

    _inherit = ['clouder.template.one2many']

    _template_parent_model = 'clouder.application'
    _template_parent_many2one = 'application_id'
    _template_fields = ['required', 'auto', 'make_link', 'container', 'base']

    application_id = fields.Many2one('clouder.application', 'Application',
                                     ondelete="cascade", required=False)
    template_id = fields.Many2one(
        'clouder.application.template', 'Template',
        ondelete="cascade", required=False)
    name = fields.Many2one('clouder.application', 'Application', required=True)
    required = fields.Boolean('Required?')
    auto = fields.Boolean('Auto?')
    make_link = fields.Boolean('Make docker link?')
    container = fields.Boolean('Container?')
    base = fields.Boolean('Base?')
    next = fields.Many2one('clouder.container', 'Next')

    _sql_constraints = [
        ('name_uniq', 'unique(application_id,template_id,name)',
         'Links must be unique per application!'),
    ]


class ClouderApplicationMetadata(models.Model):
    """
    Defines an object to store metadata linked to an application
    """

    _name = 'clouder.application.metadata'

    application_id = fields.Many2one(
        'clouder.application', 'Application', ondelete="cascade", required=True)
    name = fields.Char('Name', required=True, size=64)
    clouder_type = fields.Selection(
        [
            ('container', 'Container'),
            ('base', 'Base')
        ], 'Type', required=True)
    is_function = fields.Boolean(
        'Function', help="Is the value computed by a function?",
        required=False, default=False)
    func_name = fields.Char('Function Name', size=64)
    default_value = fields.Text('Default Value')
    value_type = fields.Selection(
        [
            ('int', 'Integer'),
            ('float', 'Float'),
            ('char', 'Char')
        ], 'Data Type', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(application_id,name, clouder_type)',
         'Metadata must be unique per application!'),
    ]

    @api.depends('is_function', 'func_name')
    @api.multi
    def _check_function(self):
        """
        Checks that the function name is defined
        and exists if is_functions is set to True
        """
        for metadata in self:
            if metadata.is_function:
                if not metadata.func_name:
                    raise except_orm(
                        _('Data error!'),
                        _("You must enter the function name "
                          "to set is_function to true.")
                    )
                else:
                    obj_env = self.env['clouder.'+self.clouder_type]
                    if not getattr(obj_env, self.func_name, False):
                        raise except_orm(
                            _('Base Metadata error!'),
                            _("Invalid function name {0} for clouder.base".
                              format(self.name.func_name))
                        )
