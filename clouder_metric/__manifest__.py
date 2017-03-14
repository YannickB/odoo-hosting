# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Clouder - Metrics",
    "summary": "Provides Usage Metric Interface for Clouder",
    "version": "10.0.1.0.0",
    "category": "Clouder",
    "website": "https://github.com/clouder-community/clouder",
    "author": "LasLabs",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        'base_external_dbsource',
        "clouder",
        "contract_variable_quantity",
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
    ],
}
