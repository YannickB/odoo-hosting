# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


from openerp import fields
from openerp import models


class ClouderApplicationTemplate(models.Model):
    """
    """

    _name = 'clouder.application.template'

    name = fields.Char('Name', required=True)
    link_ids = fields.One2many('clouder.application.link', 'template_id',
                               'Links')
