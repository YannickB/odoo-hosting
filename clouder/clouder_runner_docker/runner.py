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

from openerp import models, api, modules
import time
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)


class ClouderImage(models.Model):
    """
    Add methods to manage the docker build specificity.
    """

    _inherit = 'clouder.image'

    def build_image(
            self, model, server, runner=False, expose_ports=None, salt=True):

        if not expose_ports:
            expose_ports = []

        res = super(ClouderImage, self).build_image(
            model, server, runner=runner, expose_ports=expose_ports, salt=salt)

        if not runner or runner.application_id.type_id.name == 'docker':

            path = model.name + '-' + datetime.now().strftime('%Y%m%d.%H%M%S')
            if model._name == 'clouder.container':
                name = path
            else:
                name = model.fullpath

            if salt:
                build_dir = '/srv/salt/containers/build_' + model.name
                server = model.salt_master
            else:
                build_dir = '/tmp/' + name

            server.execute(['rm', '-rf', build_dir])
            server.execute(['mkdir', '-p', build_dir])

            if self.type_id:
                if self.type_id.name in \
                        ['backup', 'salt-master', 'salt-minion']:
                    sources_path = \
                        modules.get_module_path('clouder') + '/sources'
                else:
                    module_path = modules.get_module_path(
                        'clouder_template_' + self.type_id.name
                    )
                    sources_path = module_path and module_path + '/sources'
                if sources_path and self.env['clouder.model']\
                        .local_dir_exist(sources_path):
                    server.send_dir(sources_path, build_dir + '/sources')

            server.execute([
                'echo "' + self.computed_dockerfile.replace('"', r'\\"') +
                '" >> ' + build_dir + '/Dockerfile'])

            if expose_ports:
                server.execute([
                    'echo "' + 'EXPOSE ' + ' '.join(expose_ports) +
                    '" >> ' + build_dir + '/Dockerfile'])

            if not salt:
                server.execute(
                    ['docker', 'build', '--pull', '-t', name, build_dir])
                server.execute(['rm', '-rf', build_dir])

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
    def hook_deploy_special_cmd(self):
        return ''

    @api.multi
    def hook_deploy(self):
        """
        Deploy the container in the server.
        """

        res = super(ClouderContainer, self).hook_deploy()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name \
                == 'docker':

            res = self.get_container_res()

            if not self.application_id.check_tags(['no-salt']):

                self.deploy_salt()
                self.salt_master.execute([
                    'rm', '-rf', '/var/cache/salt/master/file_lists/roots/'])
                self.salt_master.execute([
                    'salt', self.server_id.fulldomain, 'state.apply',
                    'container_deploy',
                    "pillar=\"{'container_name': '" + self.name +
                    "', 'image': '" + self.name + '-' +
                    datetime.now().strftime('%Y%m%d.%H%M%S') +
                    "', 'build': True}\""])

            else:

                cmd = ['docker', 'run', '-d', '-t', '--restart=always']

                for port in res['ports']:
                    cmd.extend(['-p', port])
                for volume in res['volumes']:
                    cmd.extend(['-v', volume])
                for volume in res['volumes_from']:
                    cmd.extend(['--volumes-from', volume])
                for link in res['links']:
                    cmd.extend(['--link', link])
                for key, environment in res['environment'].iteritems():
                    cmd.extend(['-e', '"' + key + '"="' + environment + '"'])
                cmd = self.hook_deploy_special_args(cmd)
                cmd.extend(['--name', self.name])

                if not self.image_version_id:
                    cmd.extend([
                        self.image_id.build_image(
                            self, self.server_id,
                            expose_ports=res['expose_ports'], salt=False)])
                else:
                    cmd.extend([self.hook_deploy_source()])

                cmd.extend([self.hook_deploy_special_cmd()])

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

            if not self.application_id.check_tags(['no-salt']):
                self.salt_master.execute([
                    'salt', self.server_id.fulldomain,
                    'state.apply', 'container_purge',
                    "pillar=\"{'container_name': '" + self.name + "'}\""])
            else:
                self.server_id.execute(['docker', 'rm', '-v', self.name])

        return res

    @api.multi
    def stop_exec(self):
        """
        Stop the container.
        """

        res = super(ClouderContainer, self).stop_exec()

        if self.childs and 'exec' in self.childs:
            self.childs['exec'].stop_exec()
            return res

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name\
                == 'docker':
            if not self.application_id.check_tags(['no-salt']):
                self.salt_master.execute([
                    'salt', self.server_id.fulldomain, 'state.apply',
                    'container_stop',
                    "pillar=\"{'container_name': '" + self.name + "'}\""])
            else:
                self.server_id.execute(['docker', 'stop', self.name])

        return res

    @api.multi
    def start_exec(self):
        """
        Restart the container.
        """

        res = super(ClouderContainer, self).start_exec()

        if self.childs and 'exec' in self.childs:
            self.childs['exec'].start_exec()
            return res

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application_id.type_id.name\
                == 'docker':

            if not self.application_id.check_tags(['no-salt']):
                self.salt_master.execute([
                    'salt', self.server_id.fulldomain,
                    'state.apply', 'container_start',
                    "pillar=\"{'container_name': '" + self.name + "'}\""])
            else:
                self.server_id.execute(['docker', 'start', self.name])

            time.sleep(3)

        return res

