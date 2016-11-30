# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from openerp import models, fields, api


import logging
_logger = logging.getLogger(__name__)


class ClouderServiceChild(models.Model):
    """
    Define the service.link object, used to specify the applications linked
    to a service.
    """

    _name = 'clouder.service.child'
    _inherit = ['clouder.model']
    _autodeploy = False

    service_id = fields.Many2one(
        'clouder.service', 'Service', ondelete="cascade", required=True)
    name = fields.Many2one(
        'clouder.application', 'Application', required=True)
    sequence = fields.Integer('Sequence')
    server_id = fields.Many2one(
        'clouder.server', 'Server')
    child_id = fields.Many2one(
        'clouder.service', 'Service')
    save_id = fields.Many2one(
        'clouder.save', 'Restore this save on deployment')

    _order = 'sequence'

    @api.multi
    @api.constrains('child_id')
    def _check_child_id(self):
        if self.child_id and not self.child_id.parent_id == self:
            self.raise_error(
                "The child service is not correctly linked to the parent",
            )

    @api.multi
    def create_child(self):
        self = self.with_context(no_enqueue=True)
        self.do(
            'create_child ' + self.name.name,
            'create_child_exec', where=self.service_id)

    @api.multi
    def create_child_exec(self):
        service = self.service_id
        self = self.with_context(autocreate=True)
        self.delete_child_exec()
        self.env['clouder.service'].create({
            'environment_id': service.environment_id.id,
            'suffix': service.suffix + '-' + self.name.code,
            'parent_id': self.id,
            'application_id': self.name.id,
            'server_id': self.server_id.id or service.server_id.id
        })
        if self.save_id:
            self.save_id.service_id = self.child_id
            self.save_id.restore()

    @api.multi
    def delete_child(self):
        self = self.with_context(no_enqueue=True)
        self.do(
            'delete_child ' + self.name.name,
            'delete_child_exec', where=self.service_id)

    @api.multi
    def delete_child_exec(self):
        self.child_id and self.child_id.unlink()
