# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


try:
    from odoo import models, fields
except ImportError:
    from openerp import models, fields


class ClouderImagePort(models.Model):
    """
    Define the image.port object, which represent the ports which
    will define the ports in the generated image and which will be inherited
    in the services.
    """

    _name = 'clouder.image.port'
    _description = 'Clouder Image Port'

    _inherit = ['clouder.template.one2many']

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,template_id,name)',
         'Port name must be unique per image!')
    ]

    _template_parent_model = 'clouder.image'
    _template_parent_many2one = 'image_id'
    _template_fields = ['local_port', 'expose', 'udp', 'use_hostport']

    image_id = fields.Many2one('clouder.image', 'Image', ondelete="cascade",
                               required=False)
    template_id = fields.Many2one(
        'clouder.image.template', 'Template', ondelete="cascade")
    name = fields.Char('Name', required=True)
    local_port = fields.Char('Local port', required=True)
    expose = fields.Selection(
        [('internet', 'Internet'), ('local', 'Local'), ('none', 'None')],
        'Expose?', required=True, default='local')
    udp = fields.Boolean('UDP?')
    use_hostport = fields.Boolean('Use hostport?')
