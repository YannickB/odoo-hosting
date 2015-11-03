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


class ClouderContainer(models.Model):
    """
    Add methods to manage the docker container specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def deploy(self):
        """
        Deploy the container in the server.
        """

        res = super(ClouderContainer, self).deploy()

        if self.server_id.runner_id.name == 'docker':

            ssh = self.connect(self.server_id.name)

            cmd = ['sudo', 'docker', 'run', '-d', '--restart=always']
            nextport = self.server_id.start_port
            for port in self.port_ids:
                if not port.hostport:
                    while not port.hostport \
                            and nextport != self.server_id.end_port:
                        ports = self.env['clouder.container.port'].search(
                            [('hostport', '=', nextport),
                             ('container_id.server_id', '=', self.server_id.id)])
                        if not ports and not self.execute(ssh, [
                                'netstat', '-an', '|', 'grep', str(nextport)]):
                            port.hostport = nextport
                        nextport += 1
                udp = ''
                if port.udp:
                    udp = '/udp'
                if not port.hostport:
                    raise except_orm(
                        _('Data error!'),
                        _("We were not able to assign an hostport to the "
                          "localport " + port.localport + ".\n"
                          "If you don't want to assign one manually, make sure you"
                          " fill the port range in the server configuration, and "
                          "that all ports in that range are not already used."))
                cmd.extend(['-p', str(port.hostport) + ':' + port.localport + udp])
            for volume in self.volume_ids:
                if volume.hostpath:
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
            self.execute(ssh, cmd)

            time.sleep(3)

            self.deploy_post()

            self.start()

            ssh.close()

            #For shinken
            self.save()

        return res

    @api.multi
    def purge(self):
        """
        Remove the container.
        """
        res = super(ClouderContainer, self).purge()

        if self.server_id.runner_id.name == 'docker':

            ssh = self.connect(self.server_id.name)
            self.stop()
            self.execute(ssh, ['sudo', 'docker', 'rm', self.name])
            self.execute(ssh, ['rm', '-rf', '/opt/keys/' + self.fullname])
            ssh.close()

        return res

    @api.multi
    def stop(self):
        """
        Stop the container.
        """

        res = super(ClouderContainer, self).stop()

        if self.server_id.runner_id.name == 'docker':

            ssh = self.connect(self.server_id.name)
            self.execute(ssh, ['docker', 'stop', self.name])
            ssh.close()

        return res

    @api.multi
    def start(self):
        """
        Restart the container.
        """
        self.stop()

        res = super(ClouderContainer, self).start()

        if self.server_id.runner_id.name == 'docker':

            ssh = self.connect(self.server_id.name)
            self.execute(ssh, ['docker', 'start', self.name])
            ssh.close()
            time.sleep(3)

        return res