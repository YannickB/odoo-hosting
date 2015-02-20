# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Buron
#    Copyright 2013 Yannick Buron
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import models, fields, api, _
from openerp.exceptions import except_orm

from datetime import datetime
import execute

import logging
_logger = logging.getLogger(__name__)


class ClouderImage(models.Model):
    _name = 'clouder.image'

    name = fields.Char('Image name', size=64, required=True)
    current_version = fields.Char('Current version', size=64, required=True)
    parent_id = fields.Many2one('clouder.image', 'Parent image')
    parent_version_id = fields.Many2one('clouder.image.version', 'Parent version')
    parent_from = fields.Char('From', size=64)
    privileged = fields.Boolean('Privileged?', help="Indicate if the containers shall be in privilaged mode. Warning : Theses containers will have access to the host system.")
    registry_id = fields.Many2one('clouder.container', 'Registry')
    dockerfile = fields.Text('DockerFile')
    volume_ids = fields.One2many('clouder.image.volume', 'image_id', 'Volumes')
    port_ids = fields.One2many('clouder.image.port', 'image_id', 'Ports')
    version_ids = fields.One2many('clouder.image.version','image_id', 'Versions')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Image name must be unique!')
    ]

    @api.multi
    def get_vals(self):

        vals = {}
        vals.update(self.env.ref('clouder.clouder_settings').get_vals())

        ports = {}
        for port in self.port_ids:
            ports[port.name] = {'id': port.id, 'name': port.name, 'localport': port.localport}

        volumes = {}
        for volume in self.volume_ids:
            volumes[volume.id] = {'id': volume.id, 'name': volume.name}

        vals.update({
            'image_name': self.name,
            'image_privileged': self.privileged,
            'image_parent_id': self.parent_id and self.parent_id.id,
            'image_parent_from': self.parent_from,
            'image_ports': ports,
            'image_volumes': volumes,
            'image_dockerfile': self.dockerfile
        })

        return vals

    def build(self, cr, uid, ids, context=None):
        version_obj = self.pool.get('clouder.image.version')

        for image in self.browse(cr, uid, ids, context={}):
            if not image.dockerfile:
                continue
            if not image.registry_id and image.name != 'img_registry':
                raise except_orm(_('Date error!'),_("You need to specify the registry where the version must be stored."))
            now = datetime.now()
            version = image.current_version + '.' + now.strftime('%Y%m%d.%H%M%S')
            version_obj.create(cr, uid, {'image_id': image.id, 'name': version, 'registry_id': image.registry_id and image.registry_id.id, 'parent_id': image.parent_version_id and image.parent_version_id.id}, context=context)

    # def unlink(self, cr, uid, ids, context={}):
    #     for image in self.browse(cr, uid, ids, context=context):
    #         vals = self.get_vals(cr, uid, image.id, context=context)
    #         self.purge(cr, uid, vals, context=context)
    #     return super(clouder_image, self).unlink(cr, uid, ids, context=context)
    #
    # def purge(self, cr, uid, vals, context={}):
    #     context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
    #     execute.execute_local(['sudo','docker', 'rmi', vals['image_name'] + ':latest'], context)

class ClouderImageVolume(models.Model):
    _name = 'clouder.image.volume'

    image_id = fields.Many2one('clouder.image', 'Image', ondelete="cascade", required=True)
    name = fields.Char('Path', size=128, required=True)
    hostpath = fields.Char('Host path', size=128)
    user = fields.Char('System User', size=64)
    readonly = fields.Boolean('Readonly?')
    nosave = fields.Boolean('No save?')

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)', 'Volume name must be unique per image!')
    ]


class ClouderImagePort(models.Model):
    _name = 'clouder.image.port'

    image_id = fields.Many2one('clouder.image', 'Image', ondelete="cascade", required=True)
    name = fields.Char('Name', size=64, required=True)
    localport = fields.Char('Local port', size=12, required=True)
    expose = fields.Selection([('internet','Internet'),('local','Local'),('none','None')],'Expose?', required=True)
    udp = fields.Boolean('UDP?')

    _defaults = {
        'expose': 'none'
    }

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)', 'Port name must be unique per image!')
    ]

class ClouderImageVersion(models.Model):
    _name = 'clouder.image.version'
    _inherit = ['clouder.model']

    image_id = fields.Many2one('clouder.image','Image', ondelete='cascade', required=True)
    name = fields.Char('Version', size=64, required=True)
    parent_id = fields.Many2one('clouder.image.version', 'Parent version')
    registry_id = fields.Many2one('clouder.container', 'Registry')
    container_ids = fields.One2many('clouder.container','image_version_id', 'Containers')


    _order = 'create_date desc'

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)', 'Version name must be unique per image!')
    ]

    @api.multi
    def get_vals(self):

        vals = {}

        vals.update(self.image_id.get_vals())

        if self.parent_id:
            parent_vals = self.parent_id.get_vals()
            vals.update({
                'image_version_parent_id': parent_vals['image_version_id'],
                'image_version_parent_fullpath': parent_vals['image_version_fullpath'],
                'image_version_parent_fullpath_localhost': parent_vals['image_version_fullpath_localhost'],
                'image_version_parent_registry_server_id': parent_vals['registry_server_id'],
            })

        if self.registry_id:
            registry_vals = self.registry_id.get_vals()
            registry_port = registry_vals['container_ports']['registry']['hostport']
            vals.update({
                'registry_id': registry_vals['container_id'],
                'registry_fullname': registry_vals['container_fullname'],
                'registry_port': registry_port,
                'registry_server_id': registry_vals['server_id'],
                'registry_server_ssh_port': registry_vals['server_ssh_port'],
                'registry_server_domain': registry_vals['server_domain'],
                'registry_server_ip': registry_vals['server_ip'],
            })

        vals.update({
            'image_version_id': self.id,
            'image_version_name': self.name,
            'image_version_fullname': self.image_id.name + ':' + self.name,
        })

        if self.registry_id:
            vals.update({
                'image_version_fullpath': vals['registry_server_ip'] + ':' + vals['registry_port'] + '/' + vals['image_version_fullname'],
                'image_version_fullpath_localhost': 'localhost:' + vals['registry_port'] + '/' + vals['image_version_fullname']
            })
        else:
            vals['image_version_fullpath'] = ''

        return vals

    def unlink(self, cr, uid, ids, context=None):
        container_obj = self.pool.get('clouder.container')
        if container_obj.search(cr, uid, [('image_version_id','in',ids)], context=context):
            raise except_orm(_('Inherit error!'),_("A container is linked to this image version, you can't delete it!"))
        return super(ClouderImageVersion, self).unlink(cr, uid, ids, context=context)

    def deploy(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        ssh, sftp = execute.connect(vals['registry_server_domain'], vals['registry_server_ssh_port'], 'root', context)
        dir = '/tmp/' + vals['image_name'] + '_' + vals['image_version_fullname']
        execute.execute(ssh, ['mkdir', '-p', dir], context)

        dockerfile = 'FROM '
        if vals['image_parent_id'] and vals['image_version_parent_id']:
            if vals['registry_server_id'] == vals['image_version_parent_registry_server_id']:
                dockerfile += vals['image_version_parent_fullpath_localhost']
            else:
                dockerfile += vals['image_version_parent_fullpath']
        elif vals['image_parent_from']:
            dockerfile += vals['image_parent_from']
        else:
            raise except_orm(_('Date error!'),_("You need to specify the image to inherit!"))

        dockerfile += '\nMAINTAINER ' + vals['config_email_sysadmin'] + '\n'

        dockerfile += vals['image_dockerfile']
        for key, volume in vals['image_volumes'].iteritems():
            dockerfile += '\nVOLUME ' + volume['name']

        ports = ''
        for key, port in vals['image_ports'].iteritems():
            ports += port['localport'] + ' '
        if ports:
            dockerfile += '\nEXPOSE ' + ports

        execute.execute(ssh, ['echo "' + dockerfile.replace('"', '\\"') + '" >> ' + dir + '/Dockerfile'], context)
        execute.execute(ssh, ['sudo','docker', 'build', '-t', vals['image_version_fullname'], dir], context)
        execute.execute(ssh, ['sudo','docker', 'tag', vals['image_version_fullname'], vals['image_version_fullpath_localhost']], context)
        execute.execute(ssh, ['sudo','docker', 'push', vals['image_version_fullpath_localhost']], context)
        execute.execute(ssh, ['sudo','docker', 'rmi', vals['image_version_fullname']], context)
        execute.execute(ssh, ['sudo','docker', 'rmi', vals['image_version_fullpath_localhost']], context)
        execute.execute(ssh, ['rm', '-rf', dir], context)
        ssh.close()
        sftp.close()
        return

#In case of problems with ssh authentification
# - Make sure the /opt/keys belong to root:root with 700 rights
# - Make sure the user in the container can access the keys, and if possible make the key belong to the user with 700 rights

    def purge(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        #TODO There is currently no way to delete an image from private registry.
