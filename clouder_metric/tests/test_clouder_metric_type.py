# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError

from .common import TestCommon


class TestClouderMetricType(TestCommon):

    def test_get_metric_models(self):
        """ It should have the correct metric model types """
        exp = [
            ('clouder.base', 'Base'),
            ('clouder.service', 'Service'),
        ]
        self.assertEquals(exp, self.metric_type._get_metric_models())

    def test_save_metric_value_usererror(self):
        """ It should raise UserError when a bad query is supplied """
        with self.assertRaises(UserError):
            self.metric_type.save_metric_value(self.metric_interface)

    def test_save_metric_value_validationerror(self):
        """ It should raise ValidationError when no value is supplied """
        self.metric_interface.query_code = 'test = 0'
        with self.assertRaises(ValidationError):
            self.metric_type.save_metric_value(self.metric_interface)

    def test_save_metric_value(self):
        """ It should verify that the right metric values are saved """
        self.metric_interface.query_code = 'value = 100'
        self.metric_type.save_metric_value(self.metric_interface)
        self.assertTrue(
            self.metric_interface.metric_value_ids.mapped('value') == [100.0]
        )
