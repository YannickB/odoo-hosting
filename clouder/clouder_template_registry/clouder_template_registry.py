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

from openerp import models, api


class ClouderImageVersion(models.Model):
    """
    Avoid build an image if the application type if a registry.
    """

    _inherit = 'clouder.image.version'

    @api.multi
    def deploy(self):
        """
        Block the default deploy function for the registry.
        """
        if self.image_id.name != 'img_registry':
            return super(ClouderImageVersion, self).deploy()
        else:
            return True


class ClouderContainer(models.Model):
    """
    Add some methods to manage specificities of the registry building.
    """

    _inherit = 'clouder.container'

    @api.multi
    def hook_deploy_source(self):
        if self.image_id.name == 'img_registry':
            return self.image_version_id.fullname
        else:
            return super(ClouderContainer, self).hook_deploy_source()

    @api.multi
    def deploy(self):
        """
        Build the registry image directly when we deploy the container.
        """
        if self.image_id.name == 'img_registry':
            # ssh = self.connect(self.server_id.name)
            tmp_dir = '/tmp/' + self.image_id.name + '_' + \
                self.image_version_id.fullname
            self.execute(['mkdir', '-p', tmp_dir])
            self.execute([
                'echo "' + self.image_id.dockerfile.replace('"', '\\"') +
                '" >> ' + tmp_dir + '/Dockerfile'])
            self.execute(['sudo', 'docker', 'rmi',
                               self.image_version_id.fullname])
            self.execute(['sudo', 'docker', 'build', '-t',
                               self.image_version_id.fullname, tmp_dir])
            self.execute(['rm', '-rf', tmp_dir])

        return super(ClouderContainer, self).deploy()

    def deploy_post(self):
        """
        Regenerate the ssl certs after the registry deploy.
        """
        if self.application_id.type_id.name == 'registry':

            # ssh = self.connect(self.fullname)

            certfile = '/etc/ssl/certs/docker-registry.crt'
            keyfile = '/etc/ssl/private/docker-registry.key'

            self.execute(['rm', certfile])
            self.execute(['rm', keyfile])

            self.execute([
                'openssl', 'req', '-x509', '-nodes', '-days', '365',
                '-newkey', 'rsa:2048', '-out', certfile, ' -keyout',
                keyfile, '-subj', '"/C=FR/L=Paris/O=Clouder/CN=' +
                self.server_id.name + '"'])
            # ssh.close()

        return super(ClouderContainer, self).deploy_post()