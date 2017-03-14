# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ClouderContractLine(models.Model):
    """ It provides the link between billing and Clouder Services. """

    _name = 'clouder.contract.line'
    _description = 'Clouder Contract Lines'
    _inherits = {'account.analytic.invoice.line': 'contract_line_id'}

    contract_line_id = fields.Many2one(
        string='Recurring Line',
        comodel_name='account.analytic.invoice.line',
        index=True,
        required=True,
        ondelete='restrict',
    )
    metric_interface_id = fields.Many2one(
        string='Metric Interface',
        comodel_name='clouder.metric.interface',
        required=True,
    )
