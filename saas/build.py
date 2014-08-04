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
    _inherit = 'saas.image'

    def remove_image(self, cr, uid, id, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
#        image = self.browse(cr, uid, id, context=context)
        execute.execute_local(['sudo','docker', 'rmi', vals['image_name'] + ':latest'], context)

class saas_image_version(osv.osv):
    _inherit = 'saas.image.version'

    def build(self, cr, uid, id, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
#        version = self.browse(cr, uid, id, context=context)
        if execute.local_file_exist('/tmp/saas-conductor/Dockerfile'):
            execute.execute_local(['rm', '/tmp/saas-conductor/Dockerfile'], context)
        if not execute.local_dir_exist('/tmp/saas-conductor'):
            execute.execute_local(['mkdir', '/tmp/saas-conductor'], context)

        dockerfile = vals['image_dockerfile']
        volumes = '['
        for key, volume in vals['image_volumes'].iteritems():
            volumes += '"' + volume['name'] + '",'
        volumes += ']'
        dockerfile += '\nVOLUME ' + volumes

        ports = ''
        for key, port in vals['image_ports'].iteritems():
            ports += port['localport'] + ' '
        if ports:
            dockerfile += '\nEXPOSE ' + ports
        dockerfile += '\nCMD ["/opt/start.sh"]'

        execute.execute_write_file('/tmp/saas-conductor/Dockerfile', dockerfile, context)
        execute.execute_local(['sudo','docker', 'build', '-t', vals['image_version_fullname'],'/tmp/saas-conductor'], context)
        execute.execute_local(['sudo','docker', 'tag', vals['image_version_fullname'], vals['image_name'] + ':latest'], context)
        execute.execute_local(['rm', '/tmp/saas-conductor/Dockerfile'], context)
        return

    def purge(self, cr, uid, id, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
#        version = self.browse(cr, uid, id, context=context)
        execute.execute_local(['sudo','docker', 'rmi', vals['image_version_fullname']], context)


class saas_application(osv.osv):
    _inherit = 'saas.application'

    def get_current_version(self, cr, uid, obj, context=None):
        return False

class saas_application_version(osv.osv):
    _inherit = 'saas.application.version'

    def build_application(self, cr, uid, vals, context):
        return

    def build(self, cr, uid, id, vals, context):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if not execute.local_dir_exist(vals['app_full_archivepath']):
            execute.execute_local(['mkdir', vals['app_full_archivepath']], context)
        if execute.local_dir_exist(vals['app_version_full_archivepath']):
            execute.execute_local(['rm', '-rf', vals['app_version_full_archivepath']], context)
        execute.execute_local(['mkdir', vals['app_version_full_archivepath']], context)
        self.build_application(cr, uid, vals, context)
        execute.execute_write_file(vals['app_version_full_archivepath'] + '/VERSION.txt', vals['app_version_name'], context)
        execute.execute_local(['pwd'], context, path=vals['app_version_full_archivepath'])
        execute.execute_local(['tar', '-cvzf', '../' + vals['app_version_name'] + '.tar.gz', './*'], context, path=vals['app_version_full_archivepath'])
#chmod -R 777 $archive_path/$app/${app}-${name}/*

    def purge(self, cr, uid, id, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        execute.execute_local(['sudo','rm', '-rf', vals['app_version_full_archivepath']], context)
        execute.execute_local(['sudo','rm', vals['app_version_full_archivepath'] + '.tar.gz'], context)