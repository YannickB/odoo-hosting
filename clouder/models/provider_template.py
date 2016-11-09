# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

import logging


from openerp import api
from openerp import fields
from openerp import models


_logger = logging.getLogger(__name__)


class ClouderProviderTemplate(models.Model):

    _name = 'clouder.provider.template'
    _description = 'Provider Template'

    name = fields.Many2one('clouder.provider', 'Provider', required=True)
    image = fields.Selection(lambda s: s._get_images(), string='Image')
    size = fields.Selection(lambda s: s._get_sizes(), string='Size')

    @api.multi
    def _get_images(self):
        return [('dummy', 'Dummy')]

    @api.multi
    def _get_sizes(self):
        return [('dummy', 'Dummy')]
