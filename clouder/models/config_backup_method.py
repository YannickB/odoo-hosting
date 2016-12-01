# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from openerp import models, fields


class ClouderConfigBackupMethod(models.Model):
    """
    Define the config.backup.method object, which represent all backup method
    available for backup.
    """

    _name = 'clouder.config.backup.method'
    _description = 'Backup Method'

    name = fields.Char('Name', required=True)
