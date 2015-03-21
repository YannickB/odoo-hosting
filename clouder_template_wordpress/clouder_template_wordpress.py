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


class ClouderApplicationVersion(models.Model):
    """
    Add methods to manage the wordpress specificities.
    """

    _inherit = 'clouder.application.version'

    @api.multi
    def build_application(self):
        """
        Get the archive from official website.
        """
        super(ClouderApplicationVersion, self).build_application()
        if self.application_id.type_id.name == 'wordpress':
            ssh = self.connect(self.archive_id.fullname)
            self.execute(ssh,
                         ['wget', '-q', 'https://wordpress.org/latest.tar.gz',
                          'latest.tar.gz'], path=self.full_archivepath)
            self.execute(ssh, ['tar', '-xzf', 'latest.tar.gz'],
                         path=self.full_archivepath)
            self.execute(ssh, ['mv', 'wordpress/*', './'],
                         path=self.full_archivepath)
            self.execute(ssh, ['rm', '-rf', './*.tar.gz'],
                         path=self.full_archivepath)
            self.execute(ssh, ['rm', '-rf', 'wordpress/'],
                         path=self.full_archivepath)
            ssh.close()
        return


class ClouderBase(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_build(self):
        """
        Configure nginx.
        """
        res = super(ClouderBase, self).deploy_build()
        if self.application_id.type_id.name == 'wordpress':
            ssh = self.connect(self.service_id.container_id.fullname)
            config_file = '/etc/nginx/sites-available/' + self.fullname
            self.send(ssh,
                      modules.get_module_path('clouder_template_wordpress') +
                      '/res/nginx.config', config_file)
            self.execute(ssh, ['sed', '-i', '"s/BASE/' + self.name + '/g"',
                               config_file])
            self.execute(ssh, ['sed', '-i',
                               '"s/DOMAIN/' + self.domain_id.name + '/g"',
                               config_file])
            self.execute(ssh, ['sed', '-i',
                               '"s/PATH/' +
                               self.service_id.full_localpath_files
                               .replace('/', '\/') + '/g"', config_file])
            self.execute(ssh, ['ln', '-s',
                               '/etc/nginx/sites-available/' + self.fullname,
                               '/etc/nginx/sites-enabled/' + self.fullname])
            self.execute(ssh, ['/etc/init.d/nginx', 'reload'])
            ssh.close()

        return res

    @api.multi
    def purge_post(self):
        """
        Purge from nginx configuration.
        """
        super(ClouderBase, self).purge_post()
        if self.application_id.type_id.name == 'wordpress':
            ssh = self.connect(self.service_id.container_id.fullname)
            self.execute(ssh, ['rm', '-rf',
                               '/etc/nginx/sites-enabled/' + self.fullname])
            self.execute(ssh, [
                'rm', '-rf', '/etc/nginx/sites-available/' + self.fullname])
            self.execute(ssh, ['/etc/init.d/nginx', 'reload'])
            ssh.close()