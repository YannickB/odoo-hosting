# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from .common import TestCommon


class TestClouderMetricInterface(TestCommon):

    def test_metric_id(self):
        """ It should test to see that at least one metric_id is returned """
        self.assertTrue(len(self.metric_interface.metric_id) == 1)

    def test_name_get(self):
        """ It should return the right name """
        exp = [
            (self.metric_interface.id, 'Test Metric - 7')
        ]
        self.assertEqual(exp, self.metric_interface.name_get())
