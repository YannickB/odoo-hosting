# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestClouderContract(TransactionCase):

    def _scaffold_test(self, billing_type):
        """ It creates a contract with usage based on the ``billing_type``
         Args:
             billing_type (str): 'usage', 'threshold', 'order'
        Returns:
            None
        """
        self.partner = self.env.ref('base.res_partner_2')
        self.product = self.env.ref('product.product_product_2')
        self.product.taxes_id += self.env['account.tax'].search(
            [('type_tax_use', '=', 'sale')], limit=1)
        self.product.description_sale = 'Test Description'
        self.product.invoice_policy = billing_type
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
            'query_code': "value = 100\n"
                          "date_start = '2017-01-02'\n"
                          "date_end = '2016-01-03'\n",
        })
        self.contract = self.env['clouder.contract'].create({
            'name': 'Test Contract',
            'partner_id': self.partner.id,
            'pricelist_id': self.partner.property_product_pricelist.id,
            'recurring_invoices': True,
            'date_start': '2017-01-01',
            'recurring_next_date': '2017-02-01',
            'recurring_rule_type': 'monthly',
            'recurring_interval': 1,
        })
        self.contract_line = self.env['clouder.contract.line'].create({
            'analytic_account_id': self.contract.ref_contract_id.id,
            'product_id': self.product.id,
            'name': 'Clouder Instance Test',
            'quantity': 1,
            'uom_id': self.product.uom_id.id,
            'price_unit': 100,
            'discount': 50,
            'metric_interface_id': self.metric_interface.id,
        })

    def test_invoice_policy_map(self):
        """ It should contain the expected keys """
        self._scaffold_test('usage')
        policy_map = self.contract.invoice_policy_map
        exp = ('threshold', 'usage', 'cost', 'order', 'delivery')
        for k in exp:
            self.assertTrue(k in policy_map)

    def test_get_invoice_line_quantity_usage_based(self):
        """ It should return the expected usage quantity """
        self._scaffold_test('usage')
        self.metric_type.save_metric_value(self.metric_interface)
        invoice = self.contract.ref_contract_id._create_invoice()
        usage = self.contract.get_invoice_line_quantity(
            self.contract.ref_contract_id, self.contract_line, invoice
        )
        self.assertTrue(usage == 100.0)

    def test_get_invoice_line_quantity_usage_based_no_metric_dates(self):
        """ It should return the expected usage quantity
         but not have metrics with dates, so as to trigger a conditional """
        self._scaffold_test('usage')
        self.metric_interface.query_code = 'value = 100'
        self.metric_type.save_metric_value(self.metric_interface)
        invoice = self.contract.ref_contract_id._create_invoice()
        usage = self.contract.get_invoice_line_quantity(
            self.contract.ref_contract_id, self.contract_line, invoice
        )
        self.assertTrue(usage == 0.0)

    def test_get_invoice_line_quantity_threshold_based(self):
        """ It should return the expected threshold quantity """
        self._scaffold_test('threshold')
        invoice = self.contract.ref_contract_id._create_invoice()
        usage = self.contract.get_invoice_line_quantity(
            self.contract.ref_contract_id, self.contract_line, invoice
        )
        self.assertTrue(usage == 1.0)

    def test_get_invoice_line_quantity_flat_fee_based(self):
        """ It should return the expected flat fee quantity """
        self._scaffold_test('order')
        invoice = self.contract.ref_contract_id._create_invoice()
        usage = self.contract.get_invoice_line_quantity(
            self.contract.ref_contract_id, self.contract_line, invoice
        )
        self.assertTrue(usage == 1.0)

    def test_get_contract_by_account(self):
        """ It should return the existing contract """
        self._scaffold_test('order')
        contract = self.env['clouder.contract']._get_contract_by_account(
            self.contract.ref_contract_id
        )
        self.assertEquals(contract.id, self.contract.id)

    def test_get_contract_by_account_new(self):
        """ It should create a new contract based on the account """
        self._scaffold_test('order')
        account = self.env['account.analytic.account'].create({
            'name': 'Test Contract',
            'partner_id': self.partner.id,
            'pricelist_id': self.partner.property_product_pricelist.id,
            'recurring_invoices': True,
            'date_start': '2017-01-01',
            'recurring_next_date': '2017-02-01',
            'recurring_rule_type': 'monthly',
            'recurring_interval': 1,
        })
        contract = self.env['clouder.contract']._get_contract_by_account(
            account, True
        )
        self.assertTrue('CLOUD' in contract.name)
        self.assertEquals(
            contract.company_id.id, self.env.user.company_id.id
        )
