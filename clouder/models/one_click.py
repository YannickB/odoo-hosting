# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


try:
    from odoo import models, fields
except ImportError:
    from openerp import models, fields


class ClouderOneclick(models.Model):

    _name = 'clouder.oneclick'

    name = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
