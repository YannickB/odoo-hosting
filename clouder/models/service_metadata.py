# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from openerp import models, fields, api


import logging
_logger = logging.getLogger(__name__)


class ClouderServiceMetadata(models.Model):
    """
    Defines an object to store metadata linked to an application
    """

    _name = 'clouder.service.metadata'

    name = fields.Many2one(
        'clouder.application.metadata', 'Application Metadata',
        ondelete="cascade", required=True)
    service_id = fields.Many2one(
        'clouder.service', 'Service', ondelete="cascade", required=True)
    value_data = fields.Text('Value')

    _sql_constraints = [
        ('name_uniq', 'unique(name, service_id)',
         'Metadata must be unique per service!'),
    ]

    @property
    def value(self):
        """
        Property that returns the value formatted by type
        """
        def _missing_function():
            # If the function is missing, raise an exception
            self.raise_error(
                'Invalid function name "%s" for clouder.service',
                self.name.func_name,
            )

        # Computing the function if needed
        val_to_convert = self.value_data
        if self.name.is_function:
            val_to_convert = "{0}".format(getattr(
                self.service_id, self.name.func_name, _missing_function)())
            # If it is a function,
            # the text version should be updated for display
            self.with_context(skip_check=True).write({
                'value_data': val_to_convert})

        # Empty value
        if not val_to_convert:
            return False

        # value_type cases
        if self.name.value_type == 'int':
            return int(val_to_convert)
        elif self.name.value_type == 'float':
            return float(val_to_convert)
        # Defaults to char
        return str(val_to_convert)

    @api.multi
    @api.constrains('name')
    def _check_clouder_type(self):
        """
        Checks that the metadata is intended for services
        """
        if self.name.clouder_type != 'service':
            self.raise_error(
                "This metadata is intended for %s only.",
                self.name.clouder_type,
            )

    @api.multi
    @api.constrains('name', 'value_data')
    def _check_object(self):
        """
        Checks if the data can be loaded properly
        """
        if 'skip_check' in self.env.context and self.env.context['skip_check']:
            return
        # call the value property to see if the metadata can be loaded properly
        try:
            self.value
        except ValueError:
            # User display
            self.raise_error(
                'Invalid value for type "%s": \n\t"%s"\n',
                self.name.value_type, self.value_data,
            )
