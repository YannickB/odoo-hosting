# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


try:
    from odoo import models, fields
except ImportError:
    from openerp import models, fields


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
