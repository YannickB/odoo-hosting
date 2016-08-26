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
from .. import model


class ClouderServer(models.Model):
    """
    """

    _inherit = 'clouder.server'


    @api.multi
    def deploy(self):
        """
        """

        super(ClouderServer, self).deploy()

        if not self.env.ref('clouder.clouder_settings').salt_master_id:
            application = self.env.ref('clouder.app_salt_master')
            master = self.env['clouder.container'].create({
                'environment_id': self.environment_id.id,
                'suffix': 'salt-master',
                'application_id': application.id,
                'server_id': self.id,
            })
            self.env.ref('clouder.clouder_settings').salt_master_id = master.id
        else:
            master = self.env.ref('clouder.clouder_settings').salt_master_id

        application = self.env.ref('clouder.app_salt_minion')
        minion = self.env['clouder.container'].create({
            'environment_id': self.environment_id.id,
            'suffix': 'salt-minion',
            'application_id': application.id,
            'server_id': self.id,
        })
        self.salt_minion_id = minion.id
        master.execute(['salt-key', '-y', '--accept=' + self.name])

    @api.multi
    def purge(self):
        """
        """
        master = self.env.ref('clouder.clouder_settings').salt_master_id
        if master:
            master.execute(['rm', '/etc/salt/pki/master/minions/' + self.name])
            minion = self.env['clouder.container'].search([('environment_id', '=', self.environment_id.id), ('server_id', '=', self.id), ('suffix', '=', 'salt-minion')])
            minion.unlink()

        super(ClouderServer, self).purge()

class ClouderContainer(models.Model):
    """
    """

    _inherit = 'clouder.container'

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()

        if self.application_id.type_id.name == 'salt-master':
            self.execute(['sed', '-i', '"s/#publish_port: 4505/publish_port: ' +
                         self.ports['salt']['hostport'] + '/g"',
                         '/etc/salt/master'])
            self.execute(['sed', '-i', '"s/#ret_port: 4506/ret_port: ' +
                         self.ports['saltret']['hostport'] + '/g"',
                         '/etc/salt/master'])

                # if 'salt' in self.parent_id.container_id.childs:
                #     salt = self.parent_id.container_id.childs['salt']
                #     self.execute(['ssh-keygen', '-t', 'rsa', '-b', '4096', '-C', self.email_sysadmin, '-f', '~/.ssh/salt-master'])
                #     key = self.execute(['cat', '~/.ssh/salt-master.pub'])
                #     salt.execute(['mkdir', '-p', '/root/.ssh'])
                #     salt.execute([
                #         'echo', '"' + key + '"', '>>', '/root/.ssh/authorized_keys'
                #     ])
                #     self.execute(['chmod', '700', '~/.ssh/salt-master'])
                #     self.execute([
                #         'sed', '-i',
                #         "'/Host\ssalt-master\"/,/END\ssalt-master/d'",
                #         '~/.ssh/config'])
                #     self.execute(['echo', '"Host salt-master"', '>>', '~/.ssh/config'])
                #     self.execute(['echo', '"  HostName ' + salt.server_id.ip + '"', '>>', '~/.ssh/config'])
                #     self.execute(['echo', '"  Port ' + salt.ports['ssh']['hostport'] + '"', '>>', '~/.ssh/config'])
                #     self.execute(['echo', '"  User root"', '>>', '~/.ssh/config'])
                #     self.execute(['echo', '"  IdentityFile ~/.ssh/salt-master"', '>>', '~/.ssh/config'])
                #     self.execute(['echo', '"#END salt-master\n"', '>>', '~/.ssh/config'])


        if self.application_id.type_id.name == 'salt-minion':
            config_file = '/etc/salt/minion'
            self.execute(['sed', '-i', '"s/#master: salt/master: ' + self.env.ref('clouder.clouder_settings').salt_master_id.server_id.ip + '/g"', config_file])
            self.execute(['sed', '-i', '"s/#master_port: 4506/master_port: ' + str(self.env.ref('clouder.clouder_settings').salt_master_id.ports['saltret']['hostport']) + '/g"', config_file])
            self.execute(['sed', '-i', '"s/#id:/id: ' + self.server_id.name + '/g"', config_file])
