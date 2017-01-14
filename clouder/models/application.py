# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from datetime import datetime
import os.path
import re

try:
    from odoo import models, fields, api
except ImportError:
    from openerp import models, fields, api


class ClouderApplication(models.Model):
    """
    Define the application object, which represent the software which will be
    installed in service.
    """

    _name = 'clouder.application'
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]
    _order = 'sequence, code'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    type_id = fields.Many2one('clouder.application.type', 'Type',
                              required=True)
    template_ids = fields.Many2many(
        'clouder.application.template', 'clouder_application_template_rel',
        'application_id', 'template_id', 'Templates')
    current_version = fields.Char('Current version')
    next_node_id = fields.Many2one('clouder.node', 'Next node')
    default_image_id = fields.Many2one('clouder.image', 'Default Image',
                                       required=False)
    next_image_version_id = fields.Many2one(
        'clouder.image.version', 'Next Image Version')
    base = fields.Boolean('Can have base?')
    tag_ids = fields.Many2many(
        'clouder.application.tag', 'clouder_application_tag_rel',
        'application_id', 'tag_id', 'Tags')
    next_service_id = fields.Many2one('clouder.service', 'Next service')
    admin_name = fields.Char('Admin name')
    admin_email = fields.Char('Admin email')
    archive_id = fields.Many2one('clouder.service', 'Archive')
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
    service_ids = fields.One2many('clouder.service', 'application_id',
                                  'Services')
    update_strategy = fields.Selection([
        ('never', 'Never'), ('manual', 'Manual'), ('auto', 'Automatic')],
        string='Service Update Strategy', required=True, default='never')
    update_bases = fields.Boolean('Update bases?')
    auto_backup = fields.Boolean('Backup?')
    service_backup_ids = fields.Many2many(
        'clouder.service', 'clouder_application_service_backup_rel',
        'application_id', 'backup_id', 'Backups Services')
    service_time_between_backup = fields.Integer(
        'Minutes between each service backup', required=True, default=9999)
    service_backup_expiration = fields.Integer(
        'Days before service backup expiration', required=True, default=5)
    base_backup_ids = fields.Many2many(
        'clouder.service', 'clouder_application_base_backup_rel',
        'application_id', 'backup_id', 'Backups Bases')
    base_time_between_backup = \
        fields.Integer('Minutes between each base backup',
                       required=True, default=9999)
    base_backup_expiration = \
        fields.Integer('Days before base backup expiration',
                       required=True, default=5)
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.env['clouder.model'].user_partner)
    dummy = fields.Boolean('Dummy?')
    provider = fields.Boolean('Display Provider?')

    @property
    def fullcode(self):
        fullcode = self.code
        return fullcode

    @property
    def full_archivepath(self):
        """
        Property returning the full path to the archive
        in the archive service
        """
        return os.path.join(
            self.env['clouder.model'].archive_path,
            self.type_id.name, self.code,
        )

    @property
    def full_hostpath(self):
        """
        Property returning the full path to the archive
        in the hosting system.
        """
        return os.path.join(
            self.env['clouder.model'].services_hostpath,
            self.type_id.name, self.code,
        )

    @property
    def full_localpath(self):
        """
        Property returning the full path to the instance
        in the destination service
        """
        return os.path.join(
            self.type_id.localpath and self.type_id.localpath,
            self.type_id.name, self.code or '',
        )

    @property
    def computed_version(self):
        """
        Property returning the name of the application version
        with the current date.
        """
        return '%s.%s' % (
            self.current_version,
            datetime.now().strftime('%Y%m%d.%H%M%S'),
        )

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

    @api.multi
    @api.constrains('code', 'admin_name', 'admin_email')
    def _check_forbidden_chars_credentials_code(self):
        """
        Check that the application name does not contain any forbidden
        characters.
        """

        if not re.match(r"^[\w\d-]*$", self.code) or len(self.code) > 20:
            self.raise_error(
                "Code can only contains letters, digits and "
                "- and shall be less than 20 characters"
            )
        if self.admin_name and not re.match(r"^[\w\d_]*$", self.admin_name):
            self.raise_error(
                "Admin name can only contains letters, digits and underscore"
            )
        if self.admin_email \
                and not re.match(r"^[\w\d_@.-]*$", self.admin_email):
            self.raise_error(
                "Admin email can only contains letters, "
                "digits, underscore, - and @"
            )

    @api.multi
    @api.constrains('default_image_id', 'child_ids')
    def _check_image(self):
        """
        """
        if not self.default_image_id and not self.child_ids and not self.dummy:
            self.raise_error('You need to specify the image!')

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
            self.raise_error(
                "It's too dangerous to modify the application code!"
            )
        res = super(ClouderApplication, self).write(vals)
        if 'template_id' in vals:
            self = self.browse(self.id)
            for template in self.template_ids:
                for link in self.env['clouder.application.link'].search([
                        ('template_id', '=', template.id)]):
                    link.reset_template(records=[self])
        return res
