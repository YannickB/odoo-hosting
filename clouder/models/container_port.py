# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from openerp import fields
from openerp import models


import logging
_logger = logging.getLogger(__name__)


class ClouderContainerPort(models.Model):
    """
    Define the container.port object, used to define the ports which
    will be mapped in the container.
    """

    _name = 'clouder.container.port'

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Char('Name', required=True)
    localport = fields.Char('Local port', required=True)
    hostport = fields.Char('Host port')
    expose = fields.Selection(
        [('internet', 'Internet'), ('local', 'Local')], 'Expose?',
        required=True, default='local')
    udp = fields.Boolean('UDP?')
    use_hostport = fields.Boolean('Use hostpost?')

    _sql_constraints = [
        ('name_uniq', 'unique(container_id,name)',
         'Port name must be unique per container!'),
    ]
