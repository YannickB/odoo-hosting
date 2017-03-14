# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestCommon(TransactionCase):

    def setUp(self):
        super(TestCommon, self).setUp()
        self.metric_type = self.env['clouder.metric.type'].create({
            'name': 'Test Metric',
            'code': 'TEST',
            'metric_model': 'clouder.base',
            'uom_id': self.env.ref('product.uom_categ_wtime').id,
        })
        self.metric_interface = self.env['clouder.metric.interface'].create({
            'type_id': self.metric_type.id,
            'metric_ref': 7,
            'source_id': self.env.ref(
                'base_external_dbsource.demo_postgre').id,
            'query_code': 'print True',
        })
