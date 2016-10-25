# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


from openerp import models, fields, api


class ClouderBaseOption(models.Model):
    """
    Define the base.option object, used to define custom values specific
    to a base.
    """
    _name = 'clouder.base.option'

    base_id = fields.Many2one('clouder.base', 'Base', ondelete="cascade",
                              required=True)
    name = fields.Many2one('clouder.application.type.option', 'Option',
                           required=True)
    value = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(base_id,name)',
         'Option name must be unique per base!'),
    ]

    @api.multi
    @api.constrains('base_id')
    def _check_required(self):
        """
        Check that we specify a value for the option
        if this option is required.
        """
        if self.name.required and not self.value:
            self.raise_error(
                'You need to specify a value for the option "%s" '
                'for the base "%s".',
                self.name.name, self.base_id.name,
            )
