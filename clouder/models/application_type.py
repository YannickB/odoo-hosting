# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

import re

from openerp import models, fields, api


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

    @api.multi
    @api.constrains('name', 'system_user')
    def _check_forbidden_chars_name_sys_user(self):
        """
        Check that the application type name does not contain any forbidden
        characters.
        """
        if not all([re.match(r"^[\w\d-]*$", self.name),
                    re.match(r"^[\w\d-]*$", self.system_user)]):
            self.raise_error(
                "Name and system_user can only contain letters, "
                "digits and -"
            )
