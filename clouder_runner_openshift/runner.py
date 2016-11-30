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

import logging
_logger = logging.getLogger(__name__)


class ClouderContainer(models.Model):
    """
    Add methods to manage the docker service specificities.
    """

    _inherit = 'clouder.service'

    @api.multi
    def hook_deploy(self, ports, volumes):
        """
        Deploy the service in the server.
        """

        res = super(ClouderContainer, self).hook_deploy(ports, volumes)

        if self.server_id.runner_id.application_id.type_id.name == 'openshift':

            ports_dict = '['
            for port in ports:
                ports_dict += '{"name": "' + port.name + '", '
                ports_dict += '"protocol": "' + \
                              (port.udp and 'UDP' or 'TCP') + '",'
                ports_dict += '"port": ' + port.localport + ','
                ports_dict += '"targetPort": ' + port.hostport + ','
                ports_dict += '"nodePort": 0}'
            ports_dict += ']'

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

            _logger.info('%s', ports_dict.replace('\"', '\\"'))

            runner = self.server_id.runner_id
            service_file = '/tmp/config'
            runner.send(modules.get_module_path('clouder_runner_openshift') +
                        '/res/service.config', service_file)
            runner.execute(['sed', '-i', '"s/CONTAINER_NAME/' +
                            self.name + '/g"',
                            service_file])
            runner.execute(['sed', '-i', '"s/IMAGE_NAME/' +
                            self.image_version_id.fullpath_localhost.replace(
                                '/', r'\/') + '/g"',
                            service_file])
            runner.execute(['sed', '-i', '"s/PORTS/' +
                            ports_dict.replace('\"', '\\"') + '/g"',
                            service_file])
            runner.execute(['sed', '-i', '"s/VOLUME_MOUNTS/' +
                            str(volume_mounts_dict) + '/g"',
                            service_file])
            runner.execute(['sed', '-i', '"s/VOLUMES/' +
                            str(volumes_dict) + '/g"',
                            service_file])
            runner.execute(['oc', 'create', '-f', service_file])
            runner.execute(['rm', service_file])

        return res

    @api.multi
    def purge(self):
        """
        Remove the service.
        """
        res = super(ClouderContainer, self).purge()

        if self.server_id.runner_id.application_id.type_id.name == 'openshift':

            runner = self.server_id.runner_id
            runner.execute(['oc', 'stop', 'dc', self.name])
            runner.execute(['oc', 'delete', 'route', self.name])
            runner.execute(['oc', 'stop', 'svc', self.name])

        return res

    @api.multi
    def stop(self):
        """
        Stop the service.
        """

        res = super(ClouderContainer, self).stop()

        # if self.server_id.runner_id.name == 'docker':
        #
        #     ssh = self.connect(self.server_id.name)
        #     self.execute(ssh, ['docker', 'stop', self.name])
        #     ssh.close()

        return res

    @api.multi
    def start(self):
        """
        Restart the service.
        """

        res = super(ClouderContainer, self).start()

        # if self.server_id.runner_id.name == 'docker':
        #
        #     ssh = self.connect(self.server_id.name)
        #     self.execute(ssh, ['docker', 'start', self.name])
        #     ssh.close()
        #     time.sleep(3)

        return res
