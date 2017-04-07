# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


try:
    from odoo import models, fields
except ImportError:
    from openerp import models, fields


class ClouderImageVolume(models.Model):
    """
    Define the image.volume object, which represent the volumes which
    will define the volume in the generated image and which will be
    inherited in the services.
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
    _template_fields = ['localpath', 'hostpath',
                        'user', 'readonly', 'no_backup']

    image_id = fields.Many2one(
        'clouder.image', 'Image', ondelete="cascade", required=False)
    template_id = fields.Many2one(
        'clouder.image.template', 'Template', ondelete="cascade")
    name = fields.Char('Name', required=True)
    localpath = fields.Char('Local Path', required=True)
    hostpath = fields.Char('Host path')
    user = fields.Char('System User')
    readonly = fields.Boolean('Readonly?')
    no_backup = fields.Boolean('No backup?')
    manual_update = fields.Boolean('Reset on Manual Update?')
