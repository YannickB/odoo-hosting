# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

import logging

try:
    from odoo import models, fields, api, modules
except ImportError:
    from openerp import models, fields, api, modules

_logger = logging.getLogger(__name__)


class ClouderVolume(models.Model):
    """
    Define the volume object, which represent the volumes
    deployed by Clouder.
    """

    _name = 'clouder.volume'
    _inherit = ['clouder.model']
    _sql_constraints = [
        ('name_uniq', 'unique(name)',
         'This name already exists.'),
    ]

    name = fields.Char('Name', required=True)
    path = fields.Char('Path', required=True)
    node_id = fields.Many2one('clouder.node', 'Node', required=True)

    @api.multi
    def hook_deploy(self):
        """
        Hook which can be called by submodules to execute commands to
        deploy a volume.
        """
        return

    @api.multi
    def deploy(self):
        """
        """
        self.hook_deploy()
        super(ClouderVolume, self).deploy()

    @api.multi
    def hook_purge(self):
        """
        Hook which can be called by submodules to execute commands to
        purge a volume.
        """
        return

    @api.multi
    def purge(self):
        """
        """
        self.hook_purge()
        super(ClouderVolume, self).purge()
