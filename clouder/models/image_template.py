# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


from odoo import models, fields


class ClouderImageTemplate(models.Model):
    """
    """

    _name = 'clouder.image.template'
    _description = 'Clouder Image Template'

    name = fields.Char('Image name', required=True)
    volume_ids = fields.One2many(
        'clouder.image.volume', 'template_id', 'Volumes')
    port_ids = fields.One2many('clouder.image.port', 'template_id', 'Ports')
