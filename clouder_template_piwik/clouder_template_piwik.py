# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Buron
#    Copyright 2013 Yannick Buron
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import models, fields, api, _
from openerp import modules

class ClouderApplicationVersion(models.Model):
    _inherit = 'clouder.application.version'

    @api.multi
    def build_application(self):
        super(ClouderApplicationVersion, self).build_application()
        if self.application_id.type_id.name == 'piwik':
            ssh, sftp = self.connect(self.archive_id.fullname())
            self.execute(ssh, ['wget', '-q', 'http://builds.piwik.org/piwik.zip', 'piwik.zip'], path=self.full_archivepath())
            self.execute(ssh, ['unzip', '-q', 'piwik.zip'], path=self.full_archivepath())
            self.execute(ssh, ['mv', 'piwik/*', './'], path=self.full_archivepath())
            self.execute(ssh, ['rm', '-rf', './*.zip'],path=self.full_archivepath())
            self.execute(ssh, ['rm', '-rf', 'piwik/'], path=self.full_archivepath())
            ssh.close(), sftp.close()
        return



class ClouderBase(models.Model):
    _inherit = 'clouder.base'

    @api.multi
    def deploy_build(self):
        res = super(ClouderBase, self).deploy_build()
        if self.application_id.type_id.name == 'piwik':

            ssh, sftp = self.connect(self.service_id.container_id.fullname())
            config_file = '/etc/nginx/sites-available/' + self.fullname()
            sftp.put(modules.get_module_path('clouder_piwik') + '/res/nginx.config', config_file)
            self.execute(ssh, ['sed', '-i', '"s/BASE/' + self.name + '/g"', config_file])
            self.execute(ssh, ['sed', '-i', '"s/DOMAIN/' + self.domain_id.name + '/g"', config_file])
            self.execute(ssh, ['sed', '-i', '"s/PATH/' + self.service_id.full_localpath_file().replace('/','\/') + '/g"', config_file])
            self.execute(ssh, ['ln', '-s',  '/etc/nginx/sites-available/' + self.fullname(),  '/etc/nginx/sites-enabled/' + self.fullname()])
            self.execute(ssh, ['/etc/init.d/nginx','reload'])
            ssh.close(), sftp.close()
        return res


    @api.multi
    def purge_post(self):
        super(ClouderBase, self).purge_post()
        if self.application_id.type_id.name == 'drupal':

            ssh, sftp = self.connect(self.service_id.container_id.fullname())
            self.execute(ssh, ['rm', '-rf', '/etc/nginx/sites-enabled/' + self.fullname()])
            self.execute(ssh, ['rm', '-rf', '/etc/nginx/sites-available/' + self.fullname()])
            self.execute(ssh, ['/etc/init.d/nginx','reload'])
            ssh.close(), sftp.close()




class ClouderBaseLink(models.Model):
    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_piwik(self, piwik_id):
        return

    @api.multi
    def deploy_link(self):
        super(ClouderBaseLink, self).deploy_link()
        if self.name.name.code == 'piwik':
            ssh, sftp = self.connect(self.target.fullname())
            piwik_id = self.execute(ssh, ['mysql', self.target_base().unique_name_(), '-h ' + self.target_base().service_id.database_server(), '-u ' + self.target_base().service_id.db_user(), '-p' + self.target_base().service_id.database_password, '-se',
                '"select idsite from piwik_site WHERE name = \'' + self.base_id.fulldomain() + '\' LIMIT 1;"'])
            if not piwik_id:
                self.execute(ssh, ['mysql', self.target_base().unique_name_(), '-h ' + self.target_base().service_id.database_server(), '-u ' + self.target_base().service_id.db_user(), '-p' + self.target_base().service_id.database_password, '-se',
                    '"INSERT INTO piwik_site (name, main_url, ts_created, timezone, currency) VALUES (\'' + self.base_id.fulldomain() + '\', \'http://' + self.base_id.fulldomain() + '\', NOW(), \'Europe/Paris\', \'EUR\');"'])
                piwik_id = self.execute(ssh, ['mysql', self.target_base().unique_name_(), '-h ' + self.target_base().service_id.database_server(), '-u ' + self.target_base().service_id.db_user(), '-p' + self.target_base().service_id.database_password, '-se',
                    '"select idsite from piwik_site WHERE name = \'' + self.base_id.fulldomain() + '\' LIMIT 1;"'])
#            self.execute(ssh, ['mysql', self.target_base().unique_name_(), '-h ' + self.target_base().service_id.database_server(), '-u ' + self.target_base().service_id.db_user(), '-p' + vals['link_target_service_db_password'], '-se',
#                '"INSERT INTO piwik_access (login, idsite, access) VALUES (\'anonymous\', ' + piwik_id + ', \'view\');"'])

            ssh.close(), sftp.close()

            self.deploy_piwik(piwik_id)

    @api.multi
    def purge_link(self):
        super(ClouderBaseLink, self).purge_link()
        if self.name.name.code == 'piwik':
            ssh, sftp = self.connect(self.target.fullname())
            piwik_id = self.execute(ssh, ['mysql', self.target_base().unique_name_(), '-h ' + self.target_base().service_id.database_server(), '-u ' + self.target_base().service_id.db_user(), '-p' + self.target_base().service_id.database_password, '-se',
                '"select idsite from piwik_site WHERE name = \'' + self.base_id.fulldomain() + '\' LIMIT 1;"'])
            # if piwik_id:
            #     execute.execute(ssh, ['mysql', self.target_base().unique_name_(), '-h ' + self.target_base().service_id.database_server(), '-u ' + self.target_base().service_id.db_user(), '-p' + self.target_base().service_id.database_password, '-se',
            #         '"DELETE FROM piwik_access WHERE idsite = ' + piwik_id + ';"'])

            ssh.close(), sftp.close()