# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

try:
    from odoo import models, fields
except ImportError:
    from openerp import models, fields


import logging
_logger = logging.getLogger(__name__)


class ClouderServicePort(models.Model):
    """
    Define the service.port object, used to define the ports which
    will be mapped in the service.
    """

    _name = 'clouder.service.port'

    service_id = fields.Many2one(
        'clouder.service', 'Service', ondelete="cascade", required=True)
    name = fields.Char('Name', required=True)
    local_port = fields.Char('Local port', required=True)
    hostport = fields.Char('Host port')
    expose = fields.Selection(
        [('internet', 'Internet'), ('local', 'Local')], 'Expose?',
        required=True, default='local')
    udp = fields.Boolean('UDP?')
    use_hostport = fields.Boolean('Use hostpost?')

    _sql_constraints = [
        ('name_uniq', 'unique(service_id,name)',
         'Port name must be unique per service!'),
    ]
