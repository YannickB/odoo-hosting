# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).


try:
    from odoo import models, fields, api
except ImportError:
    from openerp import models, fields, api


import logging
import re

from ..exceptions import ClouderError

_logger = logging.getLogger(__name__)


class ClouderEnvironment(models.Model):
    """
    Define the environment object, which represent the environment where
    the service are created and link them to the allowed users.
    """

    _name = 'clouder.environment'
    _description = 'Clouder Environment'
    _sql_constraints = [
        ('prefix_uniq', 'unique(prefix)',
         'Prefix must be unique!'),
    ]

    name = fields.Char('Name', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    prefix = fields.Char('Prefix', required=False)
    user_ids = fields.Many2many(
        'res.users', 'clouder_environment_user_rel',
        'environment_id', 'user_id', 'Users')
    service_ids = fields.One2many(
        'clouder.service', 'environment_id', 'Services')

    @api.multi
    @api.constrains('prefix')
    def _check_prefix(self):
        """
        Check that the prefix does not contain any forbidden
        characters.
        Also checks that you cannot remove a prefix
        when services are linked to the environment
        """
        if self.prefix and not re.match(r"^[\w]*$", self.prefix):
            raise ClouderError(
                self,
                "Prefix can only contains letters",
            )
        if self.service_ids and not self.prefix:
            raise ClouderError(
                self,
                "You cannot have an empty prefix when "
                "services are linked",
            )

    @api.multi
    def write(self, vals):
        """
        Removes the possibility to change the prefix if services are linked
        """
        if 'prefix' in vals and self.service_ids:
            raise ClouderError(
                self,
                "You cannot have an empty prefix "
                "when services are linked",
            )

        super(ClouderEnvironment, self).write(vals)
