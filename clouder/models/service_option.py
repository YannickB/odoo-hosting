# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from openerp import models, fields, api


import logging
_logger = logging.getLogger(__name__)


class ClouderServiceOption(models.Model):
    """
    Define the service.option object, used to define custom values
    specific to a service.
    """

    _name = 'clouder.service.option'

    service_id = fields.Many2one(
        'clouder.service', 'Service', ondelete="cascade", required=True)
    name = fields.Many2one(
        'clouder.application.type.option', 'Option', required=True)
    value = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(service_id,name)',
         'Option name must be unique per service!'),
    ]

    @api.multi
    @api.constrains('service_id')
    def _check_required(self):
        """
        Check that we specify a value for the option
        if this option is required.
        """
        if self.name.required and not self.value:
            self.raise_error(
                'You need to specify a value for the option '
                '"%s" for the service "%s".',
                self.name.name, self.service_id.name,
            )
