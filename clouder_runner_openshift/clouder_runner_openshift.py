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

        if self.server_id.runner_id.application_id.type_id.name == 'openshift':


            ports_dict = []
            for port in ports:
                ports_dict.append(
                    {
                        'name': port.name,
                        'protocol': port.udp and 'UDP' or 'TCP',
                        'port': port.localport,
                        'targetPort': port.hostport,
                        'nodePort': 0
                    }
                )
                
            volume_mounts_dict = []
            volumes_dict = []
            for volume in volumes:
                volume_mounts_dict.append(
                    {
                    'name': volume.name,
                    'mountPath': volume.localpath,
                    '??': volume.hostpath,
                    'readonly': volume.readonly
                    }
                )
                volumes_dict.append(
                    {
                        'name': volume['name'],
                        'emptyDir': {
                            'medium': ''
                        }
                    }
                )

            ssh = self.connect(self.server_id.runner_id.name)
            service_file = '/opt/odoo/' + self.name + '/etc/config'
            self.send(ssh, modules.get_module_path('clouder_runner_openshift') +
                      '/res/service.config', service_file)
            self.execute(ssh, ['sed', '-i', '"s/CONTAINER_NAME/' +
                               self.name + '/g"',
                               service_file])
            self.execute(ssh, ['sed', '-i', '"s/IMAGE_NAME/' +
                               self.image_version_id.localpath + '/g"',
                               service_file])
            self.execute(ssh, ['sed', '-i', '"s/PORTS/' +
                               str(ports_dict) + '/g"',
                               service_file])
            self.execute(ssh, ['sed', '-i', '"s/VOLUME_MOUNTS/' +
                               str(volume_mounts_dict) + '/g"',
                               service_file])
            self.execute(ssh, ['sed', '-i', '"s/VOLUMES/' +
                               str(volumes_dict) + '/g"',
                               service_file])
            self.execute(ssh, ['oc', 'create', '-f', service_file])
            self.execute(ssh, ['rm', service_file])
            ssh.close()

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