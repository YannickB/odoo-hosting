# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

from openerp import models, fields, api


import logging
_logger = logging.getLogger(__name__)


class ClouderContainerLink(models.Model):
    """
    Define the container.link object, used to specify the applications linked
    to a container.
    """

    _name = 'clouder.container.link'
    _inherit = ['clouder.model']
    _autodeploy = False

    container_id = fields.Many2one(
        'clouder.container', 'Container', ondelete="cascade", required=True)
    name = fields.Many2one(
        'clouder.application', 'Application', required=True)
    target = fields.Many2one('clouder.container', 'Target')
    required = fields.Boolean('Required?')
    auto = fields.Boolean('Auto?')
    make_link = fields.Boolean('Make docker link?')
    deployed = fields.Boolean('Deployed?', readonly=True)

    @api.multi
    @api.constrains('container_id')
    def _check_required(self):
        """
        Check that we specify a value for the link
        if this link is required.
        """
        if self.required and not self.target \
                and not self.container_id.child_ids:
            self.raise_error(
                'You need to specify a link to '
                '"%s" for the container "%s".',
                self.name.name, self.container_id.name,
            )

    @api.multi
    def deploy_link(self):
        """
        Hook which can be called by submodules to execute commands when we
        deploy a link.
        """
        self.purge_link()
        self.deployed = True
        return

    @api.multi
    def purge_link(self):
        """
        Hook which can be called by submodules to execute commands when we
        purge a link.
        """
        self.deployed = False
        return

    @api.multi
    def control(self):
        """
        Make the control to know if we can launch the deploy/purge.
        """
        if self.container_id.child_ids:
            self.log('The container has children, skipping deploy link')
            return False
        if not self.target:
            self.log('The target isnt configured in the link, '
                     'skipping deploy link')
            return False
        return True

    @api.multi
    def deploy_(self):
        self = self.with_context(no_enqueue=True)
        self.do(
            'deploy_link ' + self.name.name,
            'deploy_exec', where=self.container_id)

    @api.multi
    def deploy_exec(self):
        """
        Control and call the hook to deploy the link.
        """
        self.control() and self.deploy_link()

    @api.multi
    def purge_(self):
        self = self.with_context(no_enqueue=True)
        self.do(
            'purge_link ' + self.name.name,
            'purge_exec', where=self.container_id)

    @api.multi
    def purge_exec(self):
        """
        Control and call the hook to purge the link.
        """
        self.control() and self.purge_link()
