# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://gnu.org/licenses/lgpl.html).

try:
    from odoo import models, fields, api, _
except ImportError:
    from openerp import models, fields, api, _

import re


class ClouderImageVersion(models.Model):
    """
    Define the image.version object, which represent each build of
    the image.
    """

    _name = 'clouder.image.version'
    _description = 'Clouder Image Version'
    _inherit = ['clouder.model']

    _order = 'create_date desc'

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)',
         'Version name must be unique per image!'),
    ]

    image_id = fields.Many2one(
        'clouder.image', 'Image', ondelete='cascade', required=True)
    name = fields.Char('Version', required=True)
    parent_id = fields.Many2one('clouder.image.version', 'Parent version')
    registry_id = fields.Many2one(
        'clouder.service', 'Registry', ondelete="cascade")
    service_ids = fields.One2many(
        'clouder.service', 'image_version_id', 'Services')
    child_ids = fields.One2many(
        'clouder.image.version', 'parent_id', 'Childs')

    @property
    def fullname(self):
        """
        Property returning the full name of the image version.
        """
        return '%s:%s' % (self.image_id.name, self.name)

    @property
    def registry_address(self):
        """
        Property returning the address of the registry where is hosted
        the image version.
        """
        return self.registry_id and '%s:%s' % (
            self.registry_id.base_ids[0].fulldomainnode_id.ip,
            self.registry_id.ports['http']['hostport'],
        )

    @property
    def fullpath(self):
        """
        Property returning the full path to get the image version.
        """
        return self.registry_id and '%s/%s' % (
            self.registry_address, self.fullname,
        )

    @property
    def fullpath_localhost(self):
        """
        Property returning the full path to get the image version if the
        registry is on the same node.
        """
        return self.registry_id and 'localhost:%s/%s' % (
            self.registry_id.ports['http']['hostport'], self.fullname,
        )

    @api.multi
    @api.constrains('name')
    def _check_name(self):
        """
        Check that the image version name does not contain any forbidden
        characters.
        """
        if not re.match(r"^[\w\d_.]*$", self.name):
            self.raise_error(
                "Image version can only contains letters, "
                "digits and underscore and dot.",
            )

    @api.multi
    def unlink(self):
        """
        Override unlink method to prevent image version unlink if
        some services are linked to it.
        """
        if self.service_ids:
            self.raise_error(
                _("A service is linked to this image version, "
                  "you can't delete it!"))
        if self.child_ids:
            self.raise_error(
                "A child is linked to this image version, "
                "you can't delete it!",
            )
        return super(ClouderImageVersion, self).unlink()

    @api.multi
    def hook_build(self):
        return

    @api.multi
    def control_priority(self):
        # if 'clouder_unlink' in self.env.context:
        #     for image_version in self.search([('parent_id','=',self.id)]):
        #         return image_version.check_priority()
        # else:
        return self.parent_id.check_priority()

    @api.multi
    def deploy(self):
        """
        Build a new image and store it to the registry.
        """
        self.hook_build()
        super(ClouderImageVersion, self).deploy()
        return

    # In case of problems with ssh authentification
    # - Make sure the /opt/keys belong to root:root with 700 rights
    # - Make sure the user in the service can access the keys,
    #     and if possible make the key belong to the user with 700 rights

    @api.multi
    def purge(self):
        """
        Delete an image from the private registry.
        """
        return
