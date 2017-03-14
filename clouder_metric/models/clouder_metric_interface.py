# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ClouderMetricInterface(models.Model):
    """ It provides a common interface for Clouder Usage metrics.

    This object receives all attributes from ``clouder.metric.type``.
    """

    _name = 'clouder.metric.interface'
    _description = 'Clouder Metric Interfaces'
    _inherits = {'clouder.metric.type': 'type_id'}

    type_id = fields.Many2one(
        string='Metric Type',
        comodel_name='clouder.metric.type',
        required=True,
        ondelete='restrict',
    )
    metric_value_ids = fields.One2many(
        string='Metric Values',
        comodel_name='clouder.metric.value',
        inverse_name='interface_id',
    )
    metric_model = fields.Selection(
        related='type_id.metric_model',
    )
    metric_ref = fields.Integer(
        required=True,
    )
    source_id = fields.Many2one(
        string='Metric Source',
        comodel_name='base.external.dbsource',
        domain="[('connector', '=', type_id.connector_type)]",
        required=True,
    )
    cron_id = fields.Many2one(
        string='Scheduled Task',
        comodel_name='ir.cron',
        domain="[('model', '=', _name)]",
        context="""{
            'default_model': _name,
            'default_name': '[Clouder Metric] %s' % display_name,
        }""",
    )
    interval_number = fields.Integer(
        related='cron_id.interval_number',
    )
    interval_type = fields.Selection(
        related='cron_id.interval_type',
    )
    query_code = fields.Text()

    @property
    @api.multi
    def metric_id(self):
        self.ensure_one()
        return self.env[self.metric_model].browse(
            self.metric_ref,
        )

    @api.multi
    def name_get(self):
        return [
            (r.id, '%s - %s' % (r.type_id.name, r.metric_id.id)) for r in self
        ]
