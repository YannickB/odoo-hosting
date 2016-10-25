# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


from openerp import fields
from openerp import models


class ClouderImageVolume(models.Model):
    """
    Define the image.volume object, which represent the volumes which
    will define the volume in the generated image and which will be
    inherited in the containers.
    """

    _name = 'clouder.image.volume'
    _description = 'Clouder Image Volume'

    _inherit = ['clouder.template.one2many']

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,template_id,name)',
         'Volume name must be unique per image!'),
    ]

    _template_parent_model = 'clouder.image'
    _template_parent_many2one = 'image_id'
    _template_fields = ['hostpath', 'user', 'readonly', 'nosave']

    image_id = fields.Many2one(
        'clouder.image', 'Image', ondelete="cascade", required=False)
    template_id = fields.Many2one(
        'clouder.image.template', 'Template', ondelete="cascade")
    name = fields.Char('Path', required=True)
    hostpath = fields.Char('Host path')
    user = fields.Char('System User')
    readonly = fields.Boolean('Readonly?')
    nosave = fields.Boolean('No save?')
