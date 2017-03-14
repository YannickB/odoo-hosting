# -*- coding: utf-8 -*-
# Copyright 2016-2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class ClouderContract(models.Model):
    """ It provides formulas specific to billing Clouder contracts. """

    _name = 'clouder.contract'
    _description = 'Clouder Contracts'
    _inherits = {'account.analytic.account': 'ref_contract_id'}

    ref_contract_id = fields.Many2one(
        string='Related Contract',
        comodel_name='account.analytic.account',
        index=True,
        require=True,
        ondelete='cascade',
    )

    _sql_constraints = [
        ('ref_contract_id_unique', 'UNIQUE(ref_contract_id)',
         'Cannot assign two ClouderContracts to the same Analytic Account.'),
    ]

    @property
    @api.model
    def invoice_policy_map(self):
        """ It returns a mapping of invoice policies to processing methods.

        Returns:
            dict: Mapping keyed by invoice policy type, pointing to the
                method that should determine the quantity to use for
                invoicing.
                The method will receive the recurring contract line and the
                invoice as arguments.
                See one of the methods that are already mapped for examples.
        """
        return {
            'threshold': self._get_quantity_threshold,
            'usage': self._get_quantity_usage,
            'cost': self._get_quantity_usage,
            'order': self._get_quantity_flat,
            'delivery': self._get_quantity_usage,
        }

    @api.model
    def get_invoice_line_quantity(self, account, account_line, invoice):
        """ It returns the Qty to be used for contract billing formula.

        This method should be called from ``contract.line.qty.formula`` by
        adding the following into the ``code`` field:

        .. code-block:: python

            result = env['clouder.contract'].get_invoice_line_quantity(
                contract, line, invoice,
            )

        Args:
            account (AccountAnalyticAccount): Contract that recurring
                invoice line belongs to. This is called
            account_line (AccountAnalyticInvoiceLine): Recurring invoice
                line being referenced.
            invoice (AccountInvoice): Invoice that is being created.
        Returns:
            int: Quantity to use on invoice line in the UOM defined on the
                ``contract_line``.
        """
        invoice_policy = account_line.product_id.invoice_policy
        invoice_policy_map = self.invoice_policy_map
        try:
            method = invoice_policy_map[invoice_policy]
        except KeyError:
            _logger.info(
                'No calculation method found for invoice policy "%s". '
                'Defaulting to Flat Rate instead.', invoice_policy
            )
            method = invoice_policy_map['order']
        return method(account_line, invoice)

    @api.model
    def _create_default_vals(self, account):
        """ It returns default values to create and link new ClouderContracts.

        Args:
            account (AccountAnalyticAccount): Account that ClouderContract
                will reference.
        Returns:
            dict: Values fed to ``create`` in ``_get_contract_by_account``.
        """
        number = self.env['ir.sequence'].next_by_code('clouder.contract')
        # Default to the current users company if not set
        company_id = (account.company_id and account.company_id.id or
                      self.env.user.company_id.id)
        return {
            'name': number,
            'company_id': company_id,
            'ref_contract_id': account.id,
        }

    @api.model
    def _get_contract_by_account(self, account, create=False):
        """ It returns the ClouderContract or possibly creates a new one.

        Args:
            account: (AccountAnalyticAccount) Contract to search by.
            create: (bool) True will create a new ClouderContract if one does
                not already exist.
        Returns:
            clouder.contract: Clouder contract associated with ``account``.
        """
        contract = self.search([('ref_contract_id', '=', account.id)])
        if create and not contract:
            contract = self.create(self._create_default_vals(account))
        return contract

    @api.multi
    def _get_quantity_flat(self, account_line, invoice):
        """ It returns the base quantity with no calculations
        Args:
            account_line (AccountAnalyticInvoiceLine): Recurring invoice
                line being referenced.
            invoice (AccountInvoice): Invoice that is being created.
        Returns:
            float: Quantity with no calculations performed
        """
        return account_line.quantity

    @api.multi
    def _get_quantity_threshold(self, account_line, invoice):
        """ It functions like flat rate for the most part

        Args:
            account_line (AccountAnalyticInvoiceLine): Recurring invoice
                line being referenced.
            invoice (AccountInvoice): Invoice that is being created.
        Returns:
            float: Quantity to use on invoice line in the UOM defined on the
                ``contract_line``.
        """
        return account_line.quantity

    @api.multi
    def _get_quantity_usage(self, account_line, invoice):
        """ It provides a quantity based on unbilled and used metrics
        Args:
            account_line (AccountAnalyticInvoiceLine): Recurring invoice
                line being referenced.
            invoice (AccountInvoice): Invoice that is being created.
        Returns:
            float: Quantity to use on invoice line in the UOM defined on the
                ``contract_line``.
            """
        vals = account_line.metric_interface_id.metric_value_ids
        inv_date = fields.Datetime.from_string(invoice.date_invoice)
        inv_delta = self.ref_contract_id.get_relative_delta(
            self.recurring_rule_type, self.recurring_interval
        )
        start_date = inv_date - inv_delta

        # Filter out metrics that fall within the billing period
        def filter(rec):
            if not all((rec.date_start, rec.date_end)):
                return False
            start = fields.Datetime.from_string(rec.date_start)
            end = fields.Datetime.from_string(rec.date_end)
            return start >= start_date and end <= inv_date

        return sum(vals.filtered(filter).mapped('value')) or 0.0
