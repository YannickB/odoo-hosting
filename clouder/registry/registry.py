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

from .. import execute

import logging
_logger = logging.getLogger(__name__)


class ClouderImageVersion(models.Model):
    _inherit = 'clouder.image.version'

    def deploy(self, cr, uid, vals, context={}):
        if vals['image_name'] != 'img_registry':
            return super(ClouderImageVersion, self).deploy(cr, uid, vals, context)
        else:
            return True


class ClouderContainer(models.Model):
    _inherit = 'clouder.container'
    #
    # def get_vals(self, cr, uid, ids, context={}):
    #     res = super(clouder_container, self).get_vals(cr, uid, ids, context)
    #     context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
    #     if 'apptype_name' in res and res['apptype_name'] == 'registry':
    #         res['image_version_fullname'] = 'registry'
    #     return res

    def deploy(self, cr, uid, vals, context={}):
        context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        if vals['image_name'] == 'img_registry':
            ssh, sftp = execute.connect(vals['server_domain'], vals['server_ssh_port'], 'root', context)
            dir = '/tmp/' + vals['image_name'] + '_' + vals['image_version_fullname']
            execute.execute(ssh, ['mkdir', '-p', dir], context)

            execute.execute(ssh, ['echo "' + vals['image_dockerfile'].replace('"', '\\"') + '" >> ' + dir + '/Dockerfile'], context)
            execute.execute(ssh, ['sudo','docker', 'rmi', vals['image_version_fullname']], context)
            execute.execute(ssh, ['sudo','docker', 'build', '-t', vals['image_version_fullname'], dir], context)
            execute.execute(ssh, ['rm', '-rf', dir], context)
        return super(ClouderContainer, self).deploy(cr, uid, vals, context)


