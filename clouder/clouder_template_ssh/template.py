# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

try:
    from odoo import models, api
except ImportError:
    from openerp import models, api


class ClouderService(models.Model):
    """
    Add a property.
    """

    _inherit = 'clouder.service'

    @api.multi
    def deploy_post(self):
        super(ClouderService, self).deploy_post()
        if self.application_id.type_id.name == 'ssh':
            self.execute(['mkdir /root/.ssh'])
            self.execute([
                'echo "' + self.options['ssh_publickey']['value'] +
                '" > /root/.ssh/authorized_keys'])
