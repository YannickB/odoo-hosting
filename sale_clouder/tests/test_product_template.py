# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestProductTemplate(TransactionCase):

    def test_invoice_policy(self):
        """ It should ensure the right options exist for invoice policy """
        policy = self.env['product.template']._fields['invoice_policy']
        exp = ('usage', 'threshold')
        res = []
        for item in policy.selection:
            res.append(item[0])
        for e in exp:
            self.assertTrue(e in res)
