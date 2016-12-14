# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

import logging


from odoo import api
from odoo import models


_logger = logging.getLogger(__name__)


class ClouderTemplateOne2Many(models.AbstractModel):

    _name = 'clouder.template.one2many'

    @api.multi
    def reset_template(self, records=None):

        if not records:
            records = []

        if self.template_id:
            if not records:
                records = self.env[self._template_parent_model].search(
                    [('template_ids', 'in', self.template_id.id)])
            for record in records:
                name = hasattr(self.name, 'id') and self.name.id or self.name
                childs = self.search([
                    (self._template_parent_many2one, '=', record.id),
                    ('name', '=', name)])
                vals = {}
                for field in self._template_fields:
                    vals[field] = getattr(self, field)
                if childs:
                    for child in childs:
                        child.write(vals)
                else:
                    vals.update({
                        self._template_parent_many2one: record.id,
                        'name': name})
                    self.create(vals)

    @api.model
    def create(self, vals):
        """
        """
        res = super(ClouderTemplateOne2Many, self).create(vals)
        self.reset_template()
        return res

    @api.multi
    def write(self, vals):
        """
        """
        res = super(ClouderTemplateOne2Many, self).write(vals)
        self.reset_template()
        return res
