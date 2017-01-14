# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

try:
    from odoo import models, fields, api
except ImportError:
    from openerp import models, fields, api

import re
from datetime import datetime

from ..exceptions import ClouderError


class ClouderImage(models.Model):
    """
    Define the image object, which represent the service image which
    can be generated on this clouder.
    """

    _name = 'clouder.image'
    _description = 'Clouder Image'
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Image name must be unique!')
    ]

    name = fields.Char('Image name', required=True)
    type_id = fields.Many2one('clouder.application.type', 'Application Type')
    template_ids = fields.Many2many(
        'clouder.image.template', 'clouder_image_template_rel',
        'image_id', 'template_id', 'Templates')
    parent_id = fields.Many2one('clouder.image', 'Parent image')
    parent_version_id = fields.Many2one(
        'clouder.image.version', 'Parent version')
    parent_from = fields.Char('From')
    registry_id = fields.Many2one('clouder.service', 'Registry')
    dockerfile = fields.Text('DockerFile')
    volumes_from = fields.Char('Volumes from')
    volume_ids = fields.One2many('clouder.image.volume', 'image_id', 'Volumes')
    port_ids = fields.One2many('clouder.image.port', 'image_id', 'Ports')
    version_ids = fields.One2many(
        'clouder.image.version', 'image_id', 'Versions')
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.env['clouder.model'].user_partner)

    @property
    def has_version(self):
        for version in self.version_ids:
            if not version.check_priority():
                return True
        return False

    @property
    def computed_dockerfile(self):

        dockerfile = ['FROM ']

        if self.parent_id and self.parent_version_id:
            dockerfile.append(self.parent_version_id.fullpath)
        elif self.parent_from:
            dockerfile.append(self.parent_from)
        else:
            self.raise_error(
                "You need to specify the image to inherit!",
            )

        dockerfile.append(
            '\nMAINTAINER %s\n' % (self.env['clouder.model'].email_sysadmin),
        )

        dockerfile.append(self.dockerfile or '')

        volumes = [v.name for v in self.volume_ids]
        if volumes:
            dockerfile.append('\nVOLUME %s' % ' '.join(volumes))

        ports = [p.local_port for p in self.port_ids]
        if ports:
            dockerfile.append('\nEXPOSE %s' % ' '.join(ports))

        return ''.join(dockerfile)

    @api.multi
    @api.constrains('name')
    def _check_name(self):
        """
        Check that the image name does not contain any forbidden
        characters.
        """
        if not re.match(r"^[\w\d_]*$", self.name):
            ClouderError(
                self,
                "Name can only contains letters, digits and underscore",
            )

    @api.multi
    def build_image(
            self, model, node, runner=False, expose_ports=None, salt=True):
        """
        """

        return

    @api.multi
    def build(self):
        """
        Method to generate a new image version.
        """

        if not self.registry_id:
            ClouderError(
                self,
                "You need to specify the registry "
                "where the version must be stored.",
            )
        now = datetime.now()
        version = self.current_version + '.' + now.strftime('%Y%m%d.%H%M%S')
        self.env['clouder.image.version'].create({
            'image_id': self.id, 'name': version,
            'registry_id': self.registry_id and self.registry_id.id,
            'parent_id': self.parent_version_id and self.parent_version_id.id})

    @api.model
    def create(self, vals):
        """
        """
        res = super(ClouderImage, self).create(vals)
        if 'template_ids' in vals:
            for template in res.template_ids:
                for volume in self.env['clouder.image.volume'].search(
                        [('template_id', '=', template.id)]):
                    volume.reset_template(records=[res])
                for port in self.env['clouder.image.port'].search(
                        [('template_id', '=', template.id)]):
                    port.reset_template(records=[res])
        return res

    @api.multi
    def write(self, vals):
        """
        """
        res = super(ClouderImage, self).write(vals)
        if 'template_ids' in vals:
            self = self.browse(self.id)
            for template in self.template_ids:
                for volume in self.env['clouder.image.volume'].search(
                        [('template_id', '=', template.id)]):
                    volume.reset_template(records=[self])
                for port in self.env['clouder.image.port'].search(
                        [('template_id', '=', template.id)]):
                    port.reset_template(records=[self])
        return res
