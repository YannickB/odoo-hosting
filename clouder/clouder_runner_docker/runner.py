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

from openerp import models, api, _, modules
from openerp.exceptions import except_orm
import time
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)


class ClouderImage(models.Model):
    """
    Add methods to manage the docker build specificity.
    """

    _inherit = 'clouder.image'

    def build_image(self, model, server, runner=False):

        res = super(ClouderImage, self).build_image(runner=runner)

        if not runner or runner.application_id.type_id.name == 'docker':

            path = model.name + '-' + datetime.now().strftime('%Y%m%d.%H%M%S')
            if model._name == 'clouder.container':
                name = path
            else:
                name = model.fullpath

            tmp_dir = '/tmp/' + name
            server.execute(['rm', '-rf', tmp_dir])
            server.execute(['mkdir', '-p', tmp_dir])

            if self.type_id:
                if self.type_id.name == 'backup':
                    sources_path = \
                        modules.get_module_path('clouder') + '/sources'
                else:
                    module_path = modules.get_module_path(
                        'clouder_template_' + self.type_id.name
                    )
                    sources_path = module_path and module_path + '/sources'
                if sources_path and self.env['clouder.model'].local_dir_exist(sources_path):
                    server.send_dir(sources_path, tmp_dir + '/sources')

            server.execute([
                'echo "' + self.computed_dockerfile.replace('"', '\\"') +
                '" >> ' + tmp_dir + '/Dockerfile'])

            server.execute(
                ['docker', 'build', '--pull', '-t', name, tmp_dir])
            server.execute(['rm', '-rf', tmp_dir])
            return name
        return res


class ClouderImageVersion(models.Model):
    """
    Add methods to manage the docker build specificity.
    """

    _inherit = 'clouder.image.version'

    @api.multi
    def hook_build(self):

        res = super(ClouderImageVersion, self).hook_build()

        if self.registry_id.application_id.type_id.name == 'registry':
            server = self.registry_id.server_id
            name = self.image_id.build_image(self, server)
            server.execute(
                ['docker', 'push', name])

            server.execute(['docker', 'rmi', self.name])
        return res

    @api.multi
    def purge(self):
        """
        Delete an image from the private registry.
        """

        res = super(ClouderImageVersion, self).purge()

        if self.registry_id.application_id.type_id.name == 'registry':

            img_address = self.registry_id and 'localhost:' + \
                self.registry_id.ports['http']['localport'] +\
                '/v1/repositories/' + self.image_id.name + \
                '/tags/' + self.name
            self.registry_id.execute(
                ['curl', '-o curl.txt -X', 'DELETE', img_address])

        return res


class ClouderContainer(models.Model):
    """
    Add methods to manage the docker container specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def hook_deploy_source(self):

        res = super(ClouderContainer, self).hook_deploy_source()
        if res:
            return res
        else:
            if self.server_id == self.image_version_id.registry_id.server_id:
                return self.image_version_id.fullpath_localhost
            else:
                # folder = '/etc/docker/certs.d/' +\
                #          self.image_version_id.registry_address
                # certfile = folder + '/ca.crt'
                # tmp_file = '/tmp/' + self.fullname
                # self.server_id.execute(['rm', certfile])
                # self.image_version_id.registry_id.get(
                #     '/etc/ssl/certs/docker-registry.crt', tmp_file)
                # self.server_id.execute(['mkdir', '-p', folder])
                # self.server_id.send(tmp_file, certfile)
                # self.server_id.execute_local(['rm', tmp_file])
                return self.image_version_id.fullpath

    @api.multi
    def hook_deploy_special_args(self, cmd):
        return cmd

    @api.multi
    def hook_deploy(self, ports, volumes):
        """
        Deploy the container in the server.
        """

        res = super(ClouderContainer, self).hook_deploy(ports, volumes)

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name \
                == 'docker':

            cmd = ['docker', 'run', '-d', '-t', '--restart=always']
            for port in ports:
                ip = ''
                if self.server_id.public_ip and self.application_id.type_id.name != 'registry':
                    ip = self.server_id.ip + ':'
                cmd.extend(
                    ['-p', 
                     ip
                     + str(port.hostport) + ':' + port.localport \
                     + (port.udp and '/udp' or '')])
            volumes_from = {}
            for volume in volumes:
                if volume.hostpath:
                    arg = volume.hostpath + ':' + volume.name
                    if volume.readonly:
                        arg += ':ro'
                    cmd.extend(['-v', arg])
                if volume.from_id:
                    volumes_from[volume.from_id.name] = volume.from_id.name
            for key, volume in volumes_from.iteritems():
                cmd.extend(['--volumes-from', volume])
            for link in self.link_ids:
                if link.name.make_link \
                        and link.target.server_id == self.server_id:
                    cmd.extend(['--link', link.target.name +
                                ':' + link.name.name.code])
            cmd = self.hook_deploy_special_args(cmd)
            cmd.extend(['--name', self.name])

            if not self.image_version_id:
                cmd.extend([self.image_id.build_image(self, self.server_id)])
            else:
                cmd.extend([self.hook_deploy_source()])

            # Run container
            self.server_id.execute(cmd)

        return res

    @api.multi
    def hook_purge(self):
        """
        Remove the container.
        """
        res = super(ClouderContainer, self).hook_purge()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name\
                == 'docker':

            self.server_id.execute(['docker', 'rm', self.name])

        return res

    @api.multi
    def stop_exec(self):
        """
        Stop the container.
        """

        res = super(ClouderContainer, self).stop_exec()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name\
                == 'docker':

            self.server_id.execute(['docker', 'stop', self.name])

        return res

    @api.multi
    def start_exec(self):
        """
        Restart the container.
        """

        res = super(ClouderContainer, self).start_exec()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name\
                == 'docker':

            self.server_id.execute(['docker', 'start', self.name])

            time.sleep(3)

        return res
