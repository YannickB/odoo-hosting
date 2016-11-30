# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from openerp import fields
from openerp import models


import logging
_logger = logging.getLogger(__name__)


class ClouderServiceVolume(models.Model):
    """
    Define the service.volume object, used to define the volume which
    will be saved in the service or will be linked to a directory
    in the host server.
    """

    _name = 'clouder.service.volume'

    service_id = fields.Many2one(
        'clouder.service', 'Service', ondelete="cascade", required=True)
    name = fields.Char('Name', required=True)
    localpath = fields.Char('Local Path', required=True)
    hostpath = fields.Char('Host path')
    user = fields.Char('System User')
    readonly = fields.Boolean('Readonly?')
    nosave = fields.Boolean('No save?')

    _sql_constraints = [
        ('name_uniq', 'unique(service_id,name)',
         'Volume name must be unique per service!'),
    ]
