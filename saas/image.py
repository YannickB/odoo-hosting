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


from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

import time
from datetime import datetime, timedelta
import subprocess
import paramiko
import execute

import logging
_logger = logging.getLogger(__name__)


class saas_image(osv.osv):
    _name = 'saas.image'

    _columns = {
        'name': fields.char('Image name', size=64, required=True),
        'current_version': fields.char('Current version', size=64, required=True),
        'privileged': fields.boolean('Privileged?', help="Indicate if the containers shall be in privilaged mode. Warning : Theses containers will have access to the host system."),
        'dockerfile': fields.text('DockerFile'),
        'volume_ids': fields.one2many('saas.image.volume', 'image_id', 'Volumes'),
        'port_ids': fields.one2many('saas.image.port', 'image_id', 'Ports'),
        'version_ids': fields.one2many('saas.image.version','image_id', 'Versions'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Image name must be unique!'),
    ]


    def get_vals(self, cr, uid, id, context={}):

        vals = {}

        image = self.browse(cr, uid, id, context=context)

        config = self.pool.get('ir.model.data').get_object(cr, uid, 'saas', 'saas_settings') 
        vals.update(self.pool.get('saas.config.settings').get_vals(cr, uid, context=context))

        ports = {}
        for port in image.port_ids:
            ports[port.name] = {'id': port.id, 'name': port.name, 'localport': port.localport}

        volumes = {}
        for volume in image.volume_ids:
            volumes[volume.id] = {'id': volume.id, 'name': volume.name}

        vals.update({
            'image_name': image.name,
            'image_privileged': image.privileged,
            'image_ports': ports,
            'image_volumes': volumes,
            'image_dockerfile': image.dockerfile
        })

        return vals

    def build(self, cr, uid, ids, context=None):
        version_obj = self.pool.get('saas.image.version')

        for image in self.browse(cr, uid, ids, context={}):
            if not image.dockerfile:
                continue
            now = datetime.now()
            version = image.current_version + '.' + now.strftime('%Y%m%d.%H%M')
            version_obj.create(cr, uid, {'image_id': image.id, 'name': version}, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for image in self.browse(cr, uid, ids, context=context):
            vals = self.get_vals(cr, uid, image.id, context=context)
            self.purge(cr, uid, vals, context=context)
        return super(saas_image, self).unlink(cr, uid, ids, context=context)

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        execute.execute_local(['sudo','docker', 'rmi', vals['image_name'] + ':latest'], context)

class saas_image_volume(osv.osv):
    _name = 'saas.image.volume'

    _columns = {
        'image_id': fields.many2one('saas.image', 'Image', ondelete="cascade", required=True),
        'name': fields.char('Path', size=128, required=True),
        'hostpath': fields.char('Host path', size=128),
        'user': fields.char('System User', size=64),
        'readonly': fields.boolean('Readonly?'),
        'nosave': fields.boolean('No save?'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)', 'Volume name must be unique per image!'),
    ]


class saas_image_port(osv.osv):
    _name = 'saas.image.port'

    _columns = {
        'image_id': fields.many2one('saas.image', 'Image', ondelete="cascade", required=True),
        'name': fields.char('Name', size=64, required=True),
        'localport': fields.char('Local port', size=12, required=True),
        'expose': fields.selection([('internet','Internet'),('local','Local'),('none','None')],'Expose?', required=True),
        'udp': fields.boolean('UDP?'),
    }

    _defaults = {
        'expose': 'none'
    }

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)', 'Port name must be unique per image!'),
    ]

class saas_image_version(osv.osv):
    _name = 'saas.image.version'
    _inherit = ['saas.model']

    _columns = {
        'image_id': fields.many2one('saas.image','Image', ondelete='cascade', required=True),
        'name': fields.char('Version', size=64, required=True),
        'container_ids': fields.one2many('saas.container','image_version_id', 'Containers'),
    }

    _order = 'create_date desc'

    _sql_constraints = [
        ('name_uniq', 'unique(image_id,name)', 'Version name must be unique per image!'),
    ]

    def get_vals(self, cr, uid, id, context=None):

        vals = {}

        image_version = self.browse(cr, uid, id, context=context)

        vals.update(self.pool.get('saas.image').get_vals(cr, uid, image_version.image_id.id, context=context))

        vals.update({
            'image_version_id': image_version.id,
            'image_version_name': image_version.name,
            'image_version_fullname': image_version.image_id.name + ':' + image_version.name,
        })


        return vals


    def unlink(self, cr, uid, ids, context=None):
        container_obj = self.pool.get('saas.container')
        if container_obj.search(cr, uid, [('image_version_id','in',ids)], context=context):
            raise osv.except_osv(_('Inherit error!'),_("A container is linked to this image version, you can't delete it!"))
        return super(saas_image_version, self).unlink(cr, uid, ids, context=context)

    def deploy(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        execute.execute_local(['mkdir', '-p','/opt/build/saas-conductor'], context)
        execute.execute_local(['cp', '-R', vals['config_conductor_path'] + '/saas', '/opt/build/saas-conductor/saas'], context)

        dockerfile = vals['image_dockerfile']
        for key, volume in vals['image_volumes'].iteritems():
            dockerfile += '\nVOLUME ' + volume['name']

        ports = ''
        for key, port in vals['image_ports'].iteritems():
            ports += port['localport'] + ' '
        if ports:
            dockerfile += '\nEXPOSE ' + ports

        execute.execute_write_file('/opt/build/saas-conductor/Dockerfile', dockerfile, context)
        execute.execute_local(['sudo','docker', 'build', '-t', vals['image_version_fullname'],'/opt/build/saas-conductor'], context)
        execute.execute_local(['sudo','docker', 'tag', vals['image_version_fullname'], vals['image_name'] + ':latest'], context)
        execute.execute_local(['rm', '-rf', '/opt/build/saas-conductor'], context)
        return

#In case of problems with ssh authentification
# - Make sure the /opt/keys belong to root:root with 700 rights
# - Make sure the user in the container can access the keys, and if possible make the key belong to the user with 700 rights

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        execute.execute_local(['sudo','docker', 'rmi', vals['image_version_fullname']], context)

