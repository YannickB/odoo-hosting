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

# class ClouderImageVersion(models.Model):
#     """
#     Avoid build an image if the application type if a registry.
#     """
#
#     _inherit = 'clouder.image.version'
#
#     @api.multi
#     def deploy(self):
#         """
#         Block the default deploy function for the registry.
#         """
#         if self.image_id.name not in ['img_registry_data','img_registry_exec']:
#             return super(ClouderImageVersion, self).deploy()
#         else:
#             return True


class ClouderContainer(models.Model):
    """
    Add some methods to manage specificities of the registry building.
    """

    _inherit = 'clouder.container'

    # @api.multi
    # def hook_deploy_source(self):
    #     if self.image_id.name in ['img_registry_data','img_registry_exec']:
    #         return self.image_version_id.fullname
    #     else:
    #         return super(ClouderContainer, self).hook_deploy_source()

    @api.multi
    def hook_deploy_special_args(self, cmd):
        cmd = super(ClouderContainer, self).hook_deploy_special_args(cmd)
        if self.image_id.name == 'img_registry_exec':
            cmd.extend([' -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt', '-e REGISTRY_HTTP_TLS_KEY=/certs/domain.key','-e "REGISTRY_AUTH=htpasswd"',
                        '-e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm"',
                        '-e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd'])
        return cmd

    # @api.multi
    # def deploy(self):
    #     """
    #     Build the registry image directly when we deploy the container.
    #     """
    #     if self.image_id.name in ['img_registry_data','img_registry_exec']:
    #         # ssh = self.connect(self.server_id.name)
    #         tmp_dir = '/tmp/' + self.image_id.name + '_' + \
    #             self.image_version_id.fullname
    #         server = self.server_id
    #         server.execute(['rm', '-rf', tmp_dir])
    #         server.execute(['mkdir', '-p', tmp_dir])
    #         server.execute([
    #             'echo "' + self.image_version_id.computed_dockerfile.replace('"', '\\"') +
    #             '" >> ' + tmp_dir + '/Dockerfile'])
    #         server.execute(['docker', 'rmi',
    #                         self.image_version_id.fullname])
    #         server.execute(['docker', 'build', '-t',
    #                         self.image_version_id.fullname, tmp_dir])
    #         server.execute(['rm', '-rf', tmp_dir])
    #
    #     return super(ClouderContainer, self).deploy()

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