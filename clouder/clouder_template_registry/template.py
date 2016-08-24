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

class ClouderApplicationTypeOption(models.Model):
    """
    """

    _inherit = 'clouder.application.type.option'

    @api.multi
    def generate_default(self):
        res = super(ClouderApplicationTypeOption, self).generate_default()
        if self.name == 'registry_password':
            res = model.generate_random_password(20)
        return res


class ClouderContainer(models.Model):
    """
    Add some methods to manage specificities of the registry building.
    """

    _inherit = 'clouder.container'

    @api.multi
    def hook_deploy_special_args(self, cmd):
        cmd = super(ClouderContainer, self).hook_deploy_special_args(cmd)
        if self.image_id.name == 'img_registry_exec':
            cmd.extend([' -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt', '-e REGISTRY_HTTP_TLS_KEY=/certs/domain.key','-e "REGISTRY_AUTH=htpasswd"',
                        '-e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm"',
                        '-e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd'])
        return cmd


    def deploy_post(self):
        """
        Regenerate the ssl certs after the registry deploy.
        """
        if self.application_id.type_id.name == 'registry' and self.application_id.code == 'data':

            certfile = '/certs/domain.crt'
            keyfile = '/certs/domain.key'

            self.execute(['rm', certfile])
            self.execute(['rm', keyfile])

            self.execute([
                'openssl', 'req', '-x509', '-nodes', '-days', '365',
                '-newkey', 'rsa:2048', '-out', certfile, ' -keyout',
                keyfile, '-subj', '"/C=FR/L=Paris/O=Clouder/CN=' +
                self.server_id.name + '"'])

        return super(ClouderContainer, self).deploy_post()

class ClouderContainerLink(models.Model):
    """
    Add methods to manage the registry specificities.
    """

    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):
        """
        """
        super(ClouderContainerLink, self).deploy_link()

        if self.name.name.code == 'registry':
            if 'exec' in self.target.childs:
                self.target.childs['exec'].execute(['htpasswd', '-Bbn',  self.container_id.name, self.container_id.options['registry_password']['value'], '>', 'auth/htpasswd'], executor='sh')
                self.target.childs['exec'].start()


    @api.multi
    def purge_link(self):
        """
        """
        super(ClouderContainerLink, self).purge_link()

        if self.name.name.code == 'registry':
            if 'exec' in self.target.childs:
                self.target.childs['exec'].execute([
                'sed', '-i', '"/' + self.container_id.name + '/d"', 'auth/htpasswd'], executor='sh')
                self.target.childs['exec'].start()


class ClouderBaseLink(models.Model):
    """
    Add methods to manage the registry specificities.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_link(self):
        """
        """
        super(ClouderBaseLink, self).deploy_link()

        if self.name.name.code == 'proxy' \
                and self.base_id.application_id.type_id.name == 'registry':
            registry = self.base_id.container_id.childs['exec']
            if self.base_id.cert_cert and self.base_id.cert_key:
                registry.execute([
                    'echo', '"' + self.base_id.cert_cert + '"', '>', '/certs/domain.crt'
                ], executor='sh')
                registry.execute([
                    'echo', '"' + self.base_id.cert_key + '"', '>', '/certs/domain.key'], executor='sh')
                registry.start()