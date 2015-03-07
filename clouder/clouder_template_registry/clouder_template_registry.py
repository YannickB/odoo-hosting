# -*- coding: utf-8 -*-
# #############################################################################
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

import logging

_logger = logging.getLogger(__name__)


class ClouderImageVersion(models.Model):
    _inherit = 'clouder.image.version'

    @api.multi
    def deploy(self):
        if self.image_id.name != 'img_registry':
            return super(ClouderImageVersion, self).deploy()
        else:
            return True


class ClouderContainer(models.Model):
    _inherit = 'clouder.container'

    @api.multi
    def deploy(self):
        if self.image_id.name == 'img_registry':
            ssh = self.connect(self.server_id.name)
            dir = '/tmp/' + self.image_id.name + '_' +\
                  self.image_version_id.fullname
            _logger.info('dir %s', dir)
            self.execute(ssh, ['mkdir', '-p', dir])
            self.execute(ssh, [
                'echo "' + self.image_id.dockerfile.replace('"', '\\"') +
                '" >> ' + dir + '/Dockerfile'])
            self.execute(ssh, ['sudo', 'docker', 'rmi',
                               self.image_version_id.fullname])
            self.execute(ssh, ['sudo', 'docker', 'build', '-t',
                               self.image_version_id.fullname, dir])
            self.execute(ssh, ['rm', '-rf', dir])

        return super(ClouderContainer, self).deploy()


    def deploy_post(self):

        if self.application_id.type_id.name == 'registry':

            ssh = self.connect(self.fullname)

            certfile = '/etc/ssl/certs/docker-registry.crt'
            keyfile = '/etc/ssl/private/docker-registry.key'

            self.execute(ssh, ['rm', certfile])
            self.execute(ssh, ['rm', keyfile])

            self.execute(ssh, [
                'openssl', 'req', '-x509', '-nodes', '-days', '365',
                '-newkey', 'rsa:2048', '-out', certfile, ' -keyout',
                keyfile, '-subj', '"/C=FR/L=Paris/O=Clouder/CN=' +
                self.server_id.name + '"'])
            ssh.close()

        return super(ClouderContainer, self).deploy_post()