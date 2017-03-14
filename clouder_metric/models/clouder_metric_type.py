# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tools import safe_eval
from odoo.exceptions import ValidationError, UserError


class ClouderMetricType(models.Model):
    """ It provides context for usage metric types """

    _name = 'clouder.metric.type'
    _description = 'Clouder Metric Types'

    name = fields.Char()
    code = fields.Char()
    metric_model = fields.Selection(
        selection=lambda s: s._get_metric_models(),
        required=True,
        help='Clouder entity type that this metric is related to.',
    )
    uom_id = fields.Many2one(
        string='Unit of Measure',
        comodel_name='product.uom',
        required=True,
    )
    connector_type = fields.Selection(
        selection=lambda s: s.env['base.external.dbsource'].CONNECTORS,
    )
    metric_code = fields.Text(
        required=True,
        default=lambda s: s._default_query_code(),
        help='Python code to use as query for metric.'
    )

    @api.model
    def _default_query_code(self):
        return _("# Python code. \n"
                 "Use `value = my_value` to specify the final calculated "
                 " metric value. This is required. \n"
                 "Optionally use ``uom = product_uom_record`` to change the "
                 "units that the metric is being measured in. \n"
                 "You should also add `date_start` and `date_end`, which "
                 "are `datetime` values to signify the date of occurrence of "
                 "the metric value in question. \n"
                 "# You can use the following variables: \n"
                 "#  - self: browse_record of the current ID Category \n"
                 "#  - interface: browse_record of the Metrics Interface. \n"
                 "#  - metric_model: Name of the metric model type. \n")

    @api.model
    def _get_metric_models(self):
        """ Returns a selection of available metric models
        Returns:
            list: Additional metric models
        """
        return [
            ('clouder.base', 'Base'),
            ('clouder.service', 'Service'),
        ]

    @api.multi
    def _get_query_code_context(self, interface):
        """ Returns a query context for use
        Args:
            interface (clouder.metric.interface): The interface to use
        Returns:
            dict: Dict with the context for the given iface and model
        """
        self.ensure_one()
        return {
            'interface': interface,
            'metric_model': self.metric_model,
            'self': self,
        }

    @api.model
    def save_metric_value(self, metric_interfaces):
        """ Saves a metric value from the given interface
        Args:
            metric_interfaces (clouder.metric.interface): The interface to use
        Returns:
            None
        """
        for iface in metric_interfaces:
            eval_context = iface.type_id._get_query_code_context(iface)
            try:
                safe_eval(
                    iface.query_code,
                    eval_context,
                    mode='exec',
                    nocopy=True,
                )
            except Exception as e:
                raise UserError(_(
                    'Error while evaluating metrics query:'
                    '\n %s \n %s' % (iface.name, e),
                ))
            if eval_context.get('value') is None:
                raise ValidationError(_(
                    'Metrics query did not set the `value` variable, which '
                    'is used to indicate the value that should be saved for '
                    'the query.',
                ))
            uom = eval_context.get('uom') or iface.uom_id
            iface.write({
                'metric_value_ids': [(0, 0, {
                    'value': eval_context['value'],
                    'date_start': eval_context.get('date_start'),
                    'date_end': eval_context.get('date_end'),
                    'uom_id': uom.id,
                })],
            })
