# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Sale - Clouder",
    "summary": "Provides the ability to sell Clouder instances.",
    "version": "10.0.1.0.0",
    "category": "Clouder",
    "website": "https://github.com/clouder-community/clouder",
    "author": "LasLabs",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "clouder",
        "contract",
        "sale",
        "clouder_metric",
    ],
    "data": [
        "data/sale_clouder.xml",  # Must be created before formula
        "data/contract_line_qty_formula.xml",
        "security/ir.model.access.csv",
    ],
}
