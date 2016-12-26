# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, models


class ClouderBackup(models.Model):
    """ It provides Elasticsearch context for Clouder Saves

    All methods and properties are to be prefixed with ``elastic_`` in order
    to prevent namespace clashes with existing operations, unless overloading
    and calling + returning the super.
    """

    _inherit = 'clouder.backup'

    @api.multi
    def backup_database(self):
        if self.base_id.service_id.db_type == 'elasticsearch':
            pass
        return super(ClouderBackup, self).backup_database()

    @api.multi
    def restore_database(self):
        if self.base_id.service_id.db_type == 'elasticsearch':
            pass
        return super(ClouderBackup, self).restore_database()
