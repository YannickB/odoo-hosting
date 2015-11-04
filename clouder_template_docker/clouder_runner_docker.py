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

from openerp import models, api, _
from openerp.exceptions import except_orm
import time


class ClouderImageVersion(models.Model):
    """
    Add methods to manage the docker build specificities.
    """

    _inherit = 'clouder.image.version'

    @api.multi
    def hook_build(self, dockerfile):

        res = super(ClouderImageVersion, self).hook_build(dockerfile)

        if self.registry_id.application_id.type_id.name == 'registry':

            ssh = self.connect(self.registry_id.server_id.name)
            tmp_dir = '/tmp/' + self.image_id.name + '_' + self.fullname
            self.execute(ssh, ['mkdir', '-p', tmp_dir])

            self.execute(ssh, [
                'echo "' + dockerfile.replace('"', '\\"') +
                '" >> ' + tmp_dir + '/Dockerfile'])
            self.execute(ssh,
                         ['sudo', 'docker', 'build', '-t', self.fullname, tmp_dir])
            self.execute(ssh, ['sudo', 'docker', 'tag', self.fullname,
                               self.fullpath_localhost])
            self.execute(ssh,
                         ['sudo', 'docker', 'push', self.fullpath_localhost])
            self.execute(ssh, ['sudo', 'docker', 'rmi', self.fullname])
            self.execute(ssh, ['sudo', 'docker', 'rmi', self.fullpath_localhost])
            self.execute(ssh, ['rm', '-rf', tmp_dir])
            ssh.close()
        return

    @api.multi
    def purge(self):
        """
        Delete an image from the private registry.
        """

        res = super(ClouderImageVersion, self).purge()

        if self.registry_id.application_id.type_id.name == 'registry':

            ssh = self.connect(self.registry_id.fullname)
            img_address = self.registry_id and 'localhost:' + \
                          self.registry_id.ports['registry']['localport'] +\
                          '/v1/repositories/' + self.image_id.name + '/tags/' + \
                          self.name
            self.execute(ssh, ['curl', '-o curl.txt -X', 'DELETE', img_address])
            ssh.close()

        return res


class ClouderContainer(models.Model):
    """
    Add methods to manage the docker container specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def hook_deploy(self, ports, volumes):
        """
        Deploy the container in the server.
        """

        res = super(ClouderContainer, self).hook_deploy(ports, volumes)

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application.type_id.name == 'docker':

            ssh = self.connect(self.server_id.name)

            cmd = ['sudo', 'docker', 'run', '-d', '--restart=always']
            for port in ports:
                udp = ''
                if port.udp:
                    udp = '/udp'
                cmd.extend(['-p', str(port.hostport) + ':' + port.localport + udp])
            for volume in volumes:
                arg = volume.hostpath + ':' + volume.name
                if volume.readonly:
                    arg += ':ro'
                cmd.extend(['-v', arg])
            for link in self.link_ids:
                if link.name.make_link and link.target.server_id == self.server_id:
                    cmd.extend(['--link', link.target.name +
                                ':' + link.name.name.code])
            if self.privileged:
                cmd.extend(['--privileged'])
            cmd.extend(['-v', '/opt/keys/' + self.fullname +
                        ':/opt/keys', '--name', self.name])

            if self.image_id.name == 'img_registry':
                cmd.extend([self.image_version_id.fullname])
            elif self.server_id == self.image_version_id.registry_id.server_id:
                cmd.extend([self.image_version_id.fullpath_localhost])
            else:
                folder = '/etc/docker/certs.d/' +\
                         self.image_version_id.registry_address
                certfile = folder + '/ca.crt'
                tmp_file = '/tmp/' + self.fullname
                self.execute(ssh, ['rm', certfile])
                ssh_registry = self.connect(
                    self.image_version_id.registry_id.fullname)
                self.get(ssh_registry,
                         '/etc/ssl/certs/docker-registry.crt', tmp_file)
                ssh_registry.close()
                self.execute(ssh, ['mkdir', '-p', folder])
                self.send(ssh, tmp_file, certfile)
                self.execute_local(['rm', tmp_file])
                cmd.extend([self.image_version_id.fullpath])

            # Deploy key now, otherwise the container will be angry
            # to not find the key.
            # We can't before because self.ssh_port may not be set
            self.deploy_key()

            #Run container
            self.server_id.execute(cmd)

        return res

    @api.multi
    def purge(self):
        """
        Remove the container.
        """
        res = super(ClouderContainer, self).purge()

        self.stop()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application.type_id.name == 'docker':

            ssh = self.connect(self.server_id.name)
            self.server_id.execute(['sudo', 'docker', 'rm', self.name])
            self.server_id.execute(['rm', '-rf', '/opt/keys/' + self.fullname])
            ssh.close()

        return res

    @api.multi
    def stop(self):
        """
        Stop the container.
        """

        res = super(ClouderContainer, self).stop()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application.type_id.name == 'docker':

            ssh = self.connect(self.server_id.name)
            self.server_id.execute(['docker', 'stop', self.name])
            ssh.close()

        return res

    @api.multi
    def start(self):
        """
        Restart the container.
        """

        res = super(ClouderContainer, self).start()

        if not self.server_id.runner_id or \
                self.server_id.runner_id.application.type_id.name == 'docker':

            ssh = self.connect(self.server_id.name)
            self.server_id.execute(['docker', 'start', self.name])
            ssh.close()
            time.sleep(3)

        return res