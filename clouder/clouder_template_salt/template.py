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
import yaml


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
            application = self.env.ref('clouder.application_salt_master')
            master = self.env['clouder.container'].create({
                'environment_id': self.environment_id.id,
                'suffix': 'salt-master',
                'application_id': application.id,
                'server_id': self.id,
            })
        else:
            master = self.salt_master

        application = self.env.ref('clouder.application_salt_minion')
        self.env['clouder.container'].create({
            'environment_id': self.environment_id.id,
            'suffix': 'salt-minion',
            'application_id': application.id,
            'server_id': self.id,
        })
        master.execute(['salt-key', '-y', '--accept=' + self.fulldomain])

        master.execute(['echo "  \'' + self.fulldomain + '\':\n#END ' + self.fulldomain + '" >> /srv/pillar/top.sls'])

    @api.multi
    def purge(self):
        """
        """
        master = self.salt_master
        if master:
            try:
                master.execute([
                    'sed', '-i',
                    '"/  \'' + self.fulldomain + '\'/,/END\s' + self.fulldomain + '/d"',
                    '/srv/pillar/top.sls'])
                master.execute(['rm', '/etc/salt/pki/master/minions/' + self.fulldomain])
                master.execute(['rm', '/etc/salt/pki/master/minions_denied/' + self.fulldomain])
            except:
                pass
        try:
            minion = self.env['clouder.container'].search([('environment_id', '=', self.environment_id.id), ('server_id', '=', self.id), ('suffix', '=', 'salt-minion')])
            minion.unlink()
        except:
            pass
        super(ClouderServer, self).purge()

class ClouderContainer(models.Model):
    """
    """

    _inherit = 'clouder.container'

    @api.multi
    def hook_deploy_special_args(self, cmd):
        cmd = super(ClouderContainer, self).hook_deploy_special_args(cmd)
        if self.application_id.type_id.name == 'salt-minion':
            cmd.extend(['--pid host'])
        return cmd

    @api.multi
    def deploy_salt(self):

        self.purge_salt()

        # if not self.childs_ids:
        res = self.get_container_res()
        self.image_id.build_image(self, self.salt_master, expose_ports=res['expose_ports'])

        data = {
            'name': self.name,
            'image':self.name,
            'secretkey': 'registry_password' in self.options and self.options['registry_password']['value'],
        }
        bases = {}
        if self.application_id.update_bases:
            for base in self.env['clouder.base'].search([('container_id', '=', self.id)]):
                bases[base.fullname_] = base.fullname_
            if self.parent_id:
                for base in self.env['clouder.base'].search([('container_id', '=', self.parent_id.container_id.id)]):
                    bases[base.fullname_] = base.fullname_
        data['bases'] = [base for key, base in bases.iteritems()]
        data.update(self.get_container_res())

        data = {self.name: data}

        if 'registry' in self.links:
            data[self.name + '-docker-registries'] = {
               'https://' + self.links['registry'].target.base_ids[0].fulldomain + '/v1/': {
                   'email': 'admin@example.net',
                   'username': self.name,
                   'password': self.options['registry_password']['value']
               }
            }

        data = yaml.safe_dump(data, default_flow_style=False)
        self.salt_master.execute(['echo "' + data + '" > /srv/pillar/containers/' + self.name + '.sls'])
        self.salt_master.execute(['sed', '-i', '"/' + self.server_id.fulldomain + '\':/a +++    - containers/' + self.name + '"',  '/srv/pillar/top.sls'])
        self.salt_master.execute(['sed', '-i', '"s/+++//g"', '/srv/pillar/top.sls'])
        self.salt_master.execute(['salt', self.server_id.fulldomain, 'saltutil.refresh_pillar'])

    @api.multi
    def deploy(self):
        if self.application_id.type_id.name == 'salt-master':
            if not self.env.ref('clouder.clouder_settings').salt_master_id:
                self.env.ref('clouder.clouder_settings').salt_master_id = self.id

        if self.application_id.type_id.name == 'salt-minion':
            if not self.server_id.salt_minion_id:
                self.server_id.salt_minion_id = self.id
        super(ClouderContainer, self).deploy()

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()

        if self.application_id.type_id.name == 'salt-master' and self.application_id.check_tags(['exec']):
            self.execute(['sed', '-i', '"s/#publish_port: 4505/publish_port: ' +
                         self.ports['salt']['hostport'] + '/g"',
                         '/etc/salt/master'])
            self.execute(['sed', '-i', '"s/#ret_port: 4506/ret_port: ' +
                         self.ports['saltret']['hostport'] + '/g"',
                         '/etc/salt/master'])

            certfile = '/etc/ssl/private/cert.pem'
            keyfile = '/etc/ssl/private/key.pem'

            self.execute(['rm', certfile])
            self.execute(['rm', keyfile])

            self.execute([
                'openssl', 'req', '-x509', '-nodes', '-days', '365',
                '-newkey', 'rsa:2048', '-out', certfile, ' -keyout',
                keyfile, '-subj', '"/C=FR/L=Paris/O=Clouder/CN=' +
                self.server_id.name + '"'])

        if self.application_id.type_id.name == 'salt-minion':
            config_file = '/etc/salt/minion'
            self.execute(['sed', '-i', '"s/#master: salt/master: ' + self.env.ref('clouder.clouder_settings').salt_master_id.server_id.ip + '/g"', config_file])
            self.execute(['sed', '-i', '"s/#master_port: 4506/master_port: ' + str(self.env.ref('clouder.clouder_settings').salt_master_id.ports['saltret']['hostport']) + '/g"', config_file])
            self.execute(['sed', '-i', '"s/#id:/id: ' + self.server_id.fulldomain + '/g"', config_file])

    @api.multi
    def purge_salt(self):

        if self.salt_master:
            self.salt_master.execute([
                'sed', '-i', '"/containers\/' + self.name + '/d"', '/srv/pillar/top.sls'])
            self.salt_master.execute(['rm', '-rf', '/srv/salt/containers/build_' + self.name])
            self.salt_master.execute(['rm', '-rf', '/srv/pillar/containers/' + self.name + '.sls'])


class ClouderContainerLink(models.Model):
    """
    """

    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):
        """
        """
        super(ClouderContainerLink, self).deploy_link()
        if self.name.type_id.name == 'shinken' \
                and self.container_id.application_id.type_id.name == 'salt-minion':

            self.target.deploy_shinken_server(self.container_id)

    @api.multi
    def purge_link(self):
        """
        """
        super(ClouderContainerLink, self).purge_link()
        if self.name.type_id.name == 'shinken' \
                and self.container_id.application_id.type_id.name == 'salt-minion':

            self.target.purge_shinken_server(self.container_id)

class ClouderBase(models.Model):
    """
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_salt(self):

        self.purge_salt()

        data = {
            'name': self.fullname_,
            'host':self.fulldomain,
            'user':self.admin_name,
            'password':self.admin_password,
        }
        data = yaml.safe_dump({self.fullname_: data}, default_flow_style=False)
        self.salt_master.execute(['echo "' + data + '" > /srv/pillar/bases/' + self.fullname_ + '.sls'])
        self.salt_master.execute(['sed', '-i', '"/' + self.container_id.server_id.name + '\':/a +++    - bases/' + self.fullname_ + '"',  '/srv/pillar/top.sls'])
        self.salt_master.execute(['sed', '-i', '"s/+++//g"', '/srv/pillar/top.sls'])
        self.salt_master.execute(['salt', self.container_id.server_id.fulldomain, 'saltutil.refresh_pillar'])


    @api.multi
    def purge_salt(self):

        self.salt_master.execute([
            'sed', '-i', '"/bases\/' + self.name + '/d"', '/srv/pillar/top.sls'])
        self.salt_master.execute(['rm', '-rf', '/srv/pillar/bases/' + self.name + '.sls'])

