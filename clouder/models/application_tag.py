# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

try:
    from odoo import models, fields
except ImportError:
    from openerp import models, fields


class ClouderApplicationTag(models.Model):

    _name = 'clouder.application.tag'

    name = fields.Char('Name', required=True)
    application_ids = fields.Many2many(
        'clouder.application', 'clouder_application_tag_rel',
        'tag_id', 'application_id', 'Applications')
