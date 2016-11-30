# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

import re

from openerp import models, fields, api


class ClouderDomain(models.Model):
    """
    Define the domain object, which represent all domains which can be linked
    to the bases hosted in this clouder.
    """

    _name = 'clouder.domain'
    _inherit = ['clouder.model']

    name = fields.Char('Domain name', required=True)
    organisation = fields.Char('Organisation', required=True)
    dns_id = fields.Many2one('clouder.service', 'DNS Node', required=False)
    cert_key = fields.Text('Wildcard Cert Key')
    cert_cert = fields.Text('Wildcart Cert')
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.env.user.partner_id)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]

    @api.multi
    @api.constrains('name')
    def _check_name(self):
        """
        Check that the domain name does not contain any forbidden
        characters.
        """
        if not re.match(r"^[\w\d.-]*$", self.name):
            self.raise_error(
                "Name can only contains letters, digits - and dot"
            )

    @api.multi
    def write(self, vals):

        if 'dns_id' in vals:
            self.purge()

        super(ClouderDomain, self).write(vals)

        if 'dns_id' in vals:
            self.deploy()
