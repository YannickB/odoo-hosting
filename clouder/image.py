# -*- coding: utf-8 -*-
##############################################################################
#
# Author: Yannick Buron
# Copyright 2015, TODAY Clouder SASU
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License with Attribution
# clause as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License with
# Attribution clause along with this program. If not, see
# <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import models, fields, api, _
from openerp.exceptions import except_orm
import re
from datetime import datetime


class ClouderImage(models.Model):
    """
    Define the image object, which represent the container image which
    can be generated on this clouder.
    """

    _name = 'clouder.image'

    name = fields.Char('Image name', required=True)
    type_id = fields.Many2one('clouder.application.type', 'Application Type')
    current_version = fields.Char('Current version', required=True)
    parent_id = fields.Many2one('clouder.image', 'Parent image')
    parent_version_id = fields.Many2one(
        'clouder.image.version', 'Parent version')
    parent_from = fields.Char('From')
    registry_id = fields.Many2one('clouder.container', 'Registry')
    dockerfile = fields.Text('DockerFile')
    volume_ids = fields.One2many('clouder.image.volume', 'image_id', 'Volumes')
    port_ids = fields.One2many('clouder.image.port', 'image_id', 'Ports')
    version_ids = fields.One2many(
        'clouder.image.version', 'image_id', 'Versions')
    public = fields.Boolean('Public?')
    partner_id = fields.Many2one(
        'res.partner', 'Manager',
        default=lambda self: self.env['clouder.model'].user_partner)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Image name must be unique!')
    ]

    @property
    def has_version(self):
        for version in self.version_ids:
            if not version.check_priority():
                return True
        return False

    @api.one
    @api.constrains('name')
    def _validate_data(self):
        """
        Check that the image name does not contain any forbidden
        characters.
        """
        if not re.match("^[\w\d_]*$", self.name):
            raise except_orm(_('Data error!'), _(
                "Name can only contains letters, digits and underscore"))

    @api.multi
    def build(self):
        """
        Method to generate a new image version.
        """

        if not self.registry_id and self.name != 'img_registry':
            raise except_orm(
                _('Date error!'),
                _("You need to specify the registry "
                  "where the version must be stored."))
        now = datetime.now()
        version = self.current_version + '.' + now.strftime('%Y%m%d.%H%M%S')
        self.env['clouder.image.version'].create({
            'image_id': self.id, 'name': version,
            'registry_id': self.registry_id and self.registry_id.id,
            'parent_id': self.parent_version_id and self.parent_version_id.id})


class ClouderImageVolume(models.Model):
    """
    Define the image.volume object, which represent the volumes which
    will define the volume in the generated image and which will be
    inherited in the containers.
    """

    _name = 'clouder.image.volume'

    image_id = fields.Many2one('clouder.image', 'Image', ondelete="cascade",
                               required=True)
    name = fields.Char('Path', required=True)
    from_code = fields.Char('From')
    hostpath = fields.Char('Host path')
    user = fields.Char('System User')
    readonly = fields.Boolean('Readonly?')
    nosave = fields.Boolean('No save?')

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)',
         'Volume name must be unique per image!')
    ]


class ClouderImagePort(models.Model):
    """
    Define the image.port object, which represent the ports which
    will define the ports in the generated image and which will be inherited
    in the containers.
    """

    _name = 'clouder.image.port'

    image_id = fields.Many2one('clouder.image', 'Image', ondelete="cascade",
                               required=True)
    name = fields.Char('Name', required=True)
    localport = fields.Char('Local port', required=True)
    expose = fields.Selection(
        [('internet', 'Internet'), ('local', 'Local'), ('none', 'None')],
        'Expose?', required=True, default='local')
    udp = fields.Boolean('UDP?')

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)',
         'Port name must be unique per image!')
    ]


class ClouderImageVersion(models.Model):
    """
    Define the image.version object, which represent each build of
    the image.
    """

    _name = 'clouder.image.version'
    _inherit = ['clouder.model']

    image_id = fields.Many2one(
        'clouder.image', 'Image', ondelete='cascade', required=True)
    name = fields.Char('Version', required=True)
    parent_id = fields.Many2one('clouder.image.version', 'Parent version')
    registry_id = fields.Many2one(
        'clouder.container', 'Registry', ondelete="cascade")
    container_ids = fields.One2many(
        'clouder.container', 'image_version_id', 'Containers')
    child_ids = fields.One2many(
        'clouder.image.version', 'parent_id', 'Childs')

    @property
    def fullname(self):
        """
        Property returning the full name of the image version.
        """
        return self.image_id.name + ':' + self.name

    @property
    def registry_address(self):
        """
        Property returning the address of the registry where is hosted
        the image version.
        """
        return self.registry_id and self.registry_id.server_id.ip + ':' + \
            self.registry_id.ports['registry-ssl']['hostport']

    @property
    def fullpath(self):
        """
        Property returning the full path to get the image version.
        """
        return self.registry_id and self.registry_address + \
            '/' + self.fullname

    @property
    def fullpath_localhost(self):
        """
        Property returning the full path to get the image version if the
        registry is on the same server.
        """
        return self.registry_id and 'localhost:' + \
            self.registry_id.ports['registry']['hostport'] +\
            '/' + self.fullname

    _order = 'create_date desc'

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)',
         'Version name must be unique per image!')
    ]

    @api.one
    @api.constrains('name')
    def _validate_data(self):
        """
        Check that the image version name does not contain any forbidden
        characters.
        """
        if not re.match("^[\w\d_.]*$", self.name):
            raise except_orm(_('Data error!'), _(
                "Image version can only contains letters, "
                "digits and underscore and dot"))

    @api.one
    def unlink(self):
        """
        Override unlink method to prevent image version unlink if
        some containers are linked to it.
        """
        if self.container_ids:
            raise except_orm(
                _('Inherit error!'),
                _("A container is linked to this image version, "
                  "you can't delete it!"))
        if self.child_ids:
            raise except_orm(
                _('Inherit error!'),
                _("A child is linked to this image version, "
                  "you can't delete it!"))
        return super(ClouderImageVersion, self).unlink()

    @api.multi
    def hook_build(self, dockerfile):
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

        dockerfile = 'FROM '
        if self.image_id.parent_id and self.parent_id:
            if self.registry_id.server_id == \
                    self.parent_id.registry_id.server_id:
                dockerfile += self.parent_id.fullpath_localhost
            else:
                dockerfile += self.parent_id.fullpath
        elif self.image_id.parent_from:
            dockerfile += self.image_id.parent_from
        else:
            raise except_orm(_('Data error!'),
                             _("You need to specify the image to inherit!"))

        dockerfile += '\nMAINTAINER ' + self.email_sysadmin + '\n'

        dockerfile += self.image_id.dockerfile or ''
        for volume in self.image_id.volume_ids:
            dockerfile += '\nVOLUME ' + volume.name

        ports = ''
        for port in self.image_id.port_ids:
            ports += port.localport + ' '
        if ports:
            dockerfile += '\nEXPOSE ' + ports

        self.hook_build(dockerfile)

        return

    # In case of problems with ssh authentification
    # - Make sure the /opt/keys belong to root:root with 700 rights
    # - Make sure the user in the container can access the keys,
    #     and if possible make the key belong to the user with 700 rights

    @api.multi
    def purge(self):
        """
        Delete an image from the private registry.
        """
        return
