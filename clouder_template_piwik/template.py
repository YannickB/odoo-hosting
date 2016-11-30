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
from openerp import modules

#
# class ClouderApplicationVersion(models.Model):
#     """
#     Add methods to manage the piwik specificities.
#     """
#
#     _inherit = 'clouder.application.version'
#
#     @api.multi
#     def build_application(self):
#         """
#         Get the archive from official website.
#         """
#         super(ClouderApplicationVersion, self).build_application()
#         if self.application_id.type_id.name == 'piwik':
#             ssh = self.connect(self.archive_id.fullname)
#             self.execute(ssh,
#                          ['wget', '-q', 'http://builds.piwik.org/piwik.zip',
#                           'piwik.zip'], path=self.full_archivepath)
#             self.execute(ssh, ['unzip', '-q', 'piwik.zip'],
#                          path=self.full_archivepath)
#             self.execute(ssh, ['mv', 'piwik/*', './'],
#                          path=self.full_archivepath)
#             self.execute(ssh, ['rm', '-rf', './*.zip'],
#                          path=self.full_archivepath)
#             self.execute(ssh, ['rm', '-rf', 'piwik/'],
#                          path=self.full_archivepath)
#             ssh.close()
#         return


class ClouderBase(models.Model):
    """
    Add methods to manage the piwik specificities.
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_build(self):
        """
        Configure nginx.
        """
        res = super(ClouderBase, self).deploy_build()
        if self.application_id.type_id.name == 'piwik':
            ssh = self.connect(self.service_id.service_id.fullname)
            config_file = '/etc/nginx/sites-available/' + self.fullname
            self.send(ssh, modules.get_module_path(
                'clouder_template_piwik') + '/res/nginx.config', config_file)
            self.execute(ssh, ['sed', '-i', '"s/BASE/' + self.name + '/g"',
                               config_file])
            self.execute(ssh, ['sed', '-i',
                               '"s/DOMAIN/' + self.domain_id.name + '/g"',
                               config_file])
            self.execute(ssh, ['sed', '-i',
                               '"s/PATH/' +
                               self.service_id.full_localpath_files
                               .replace('/', r'\/') + '/g"', config_file])
            self.execute(ssh, ['ln', '-s',
                               '/etc/nginx/sites-available/' + self.fullname,
                               '/etc/nginx/sites-enabled/' + self.fullname])
            self.execute(ssh, ['/etc/init.d/nginx', 'reload'])
            ssh.close()
        return res

    @api.multi
    def purge_post(self):
        """
        Purge nginx configuration.
        """
        super(ClouderBase, self).purge_post()
        if self.application_id.type_id.name == 'piwik':
            ssh = self.connect(self.service_id.service_id.fullname)
            self.execute(ssh, [
                'rm', '-rf', '/etc/nginx/sites-enabled/' + self.fullname])
            self.execute(ssh, [
                'rm', '-rf', '/etc/nginx/sites-available/' + self.fullname])
            self.execute(ssh, ['/etc/init.d/nginx', 'reload'])
            ssh.close()


class ClouderBaseLink(models.Model):
    """
    Add methods to manage the piwik specificities.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_piwik(self, piwik_id):
        """
        Hook which can be called by submodules to execute commands when we
        deploy a link to piwik.

        :param piwik_id: The id of the website in piwik.
        """
        return

    @api.multi
    def deploy_link(self):
        """
        Add the website in piwik.
        """
        super(ClouderBaseLink, self).deploy_link()
        if self.name.type_id.name == 'piwik':
            ssh = self.connect(self.target.fullname)
            piwik_id = self.execute(ssh, [
                'mysql', self.target_base.fullname_,
                '-h ' + self.target_base.service_id.database_node,
                '-u ' + self.target_base.service_id.db_user,
                '-p' + self.target_base.service_id.database_password,
                '-se', '"select idsite from piwik_site WHERE name = \'' +
                self.base_id.fulldomain + '\' LIMIT 1;"'])
            if not piwik_id:
                self.execute(ssh, [
                    'mysql', self.target_base.fullname_,
                    '-h ' + self.target_base.service_id.database_node,
                    '-u ' + self.target_base.service_id.db_user,
                    '-p' + self.target_base.service_id.database_password,
                    '-se', '"INSERT INTO piwik_site (name, main_url, '
                           'ts_created, timezone, currency) VALUES (\'' +
                    self.base_id.fulldomain + '\', \'http://' +
                    self.base_id.fulldomain +
                    '\', NOW(), \'Europe/Paris\', \'EUR\');"'])
                piwik_id = self.execute(ssh, [
                    'mysql', self.target_base.fullname_,
                    '-h ' + self.target_base.service_id.database_node,
                    '-u ' + self.target_base.service_id.db_user,
                    '-p' + self.target_base.service_id.database_password,
                    '-se', '"select idsite from piwik_site WHERE name = \'' +
                    self.base_id.fulldomain + '\' LIMIT 1;"'])
                # self.execute(ssh, [
                #     'mysql', self.target_base.fullname_,
                #     '-h ' + self.target_base.service_id.database_node,
                #     '-u ' + self.target_base.service_id.db_user,
                #     '-p' + vals['link_target_service_db_password'], '-se',
                #     '"INSERT INTO piwik_access (login, idsite, access) '
                #     'VALUES (\'anonymous\', ' + piwik_id + ', \'view\');"'])

            ssh.close()

            self.deploy_piwik(piwik_id)

    @api.multi
    def purge_link(self):
        """
        Remove the website from piwik.
        """
        super(ClouderBaseLink, self).purge_link()
        if self.name.type_id.name == 'piwik':
            ssh = self.connect(self.target.fullname)
            # piwik_id = \
            self.execute(ssh, [
                'mysql', self.target_base.fullname_,
                '-h ' + self.target_base.service_id.database_node,
                '-u ' + self.target_base.service_id.db_user,
                '-p' + self.target_base.service_id.database_password,
                '-se', '"select idsite from piwik_site WHERE name = \'' +
                self.base_id.fulldomain + '\' LIMIT 1;"'])
            # if piwik_id:
            #     execute.execute(ssh, [
            #         'mysql', self.target_base.fullname_,
            #         '-h ' + self.target_base.service_id.database_node,
            #         '-u ' + self.target_base.service_id.db_user,
            #         '-p' + self.target_base.service_id.database_password,
            #         '-se', '"DELETE FROM piwik_access '
            #                'WHERE idsite = ' + piwik_id + ';"'])

            ssh.close()
