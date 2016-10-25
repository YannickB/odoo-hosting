# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


from openerp import models, fields, api

from ..tools import generate_random_password


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
            res = generate_random_password(20)
        if self.name == 'secret':
            res = generate_random_password(50)
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
