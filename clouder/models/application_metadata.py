# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


from openerp import models, fields, api


class ClouderApplicationMetadata(models.Model):
    """
    Defines an object to store metadata linked to an application
    """

    _name = 'clouder.application.metadata'

    application_id = fields.Many2one(
        'clouder.application', 'Application',
        ondelete="cascade", required=True)
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
                    self.raise_error(
                        "You must enter the function name "
                        "to set is_function to true."
                    )
                else:
                    obj_env = self.env['clouder.'+self.clouder_type]
                    if not getattr(obj_env, self.func_name, False):
                        self.raise_error(
                            "Invalid function name %s for clouder.base",
                            self.name.func_name,
                        )
