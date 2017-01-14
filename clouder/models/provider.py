# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

import logging

try:
    from odoo import models, fields, api
except ImportError:
    from openerp import models, fields, api


_logger = logging.getLogger(__name__)

try:
    import libcloud
except ImportError:
    _logger.warning('Cannot `import libcloud`.')


class ClouderProvider(models.Model):

    _name = 'clouder.provider'
    _description = 'Provider'

    name = fields.Selection(lambda s: s._get_providers(), required=True)
    config_id = fields.Many2one('clouder.config.settings',
                                'Configuration', required=True)
    type = fields.Selection(lambda s: s._get_types(), required=True)
    login = fields.Char('Login')
    secret_key = fields.Char('Secret Key')
    smtp_relayhost = fields.Char('SMTP Relay')

    @api.multi
    def _get_types(self):
        return [
            ('node', 'Node'), ('service', 'Service'),
            ('dns', 'DNS'), ('load', 'Load Balancing'),
            ('backup', 'Backup'), ('smtp', 'SMTP')]

    @api.multi
    def _get_providers(self):
        providers = []
        for key in sorted(libcloud.compute.providers.Provider.__dict__.keys()):
            if '__'not in key:
                providers.append((key, key))
        return providers
