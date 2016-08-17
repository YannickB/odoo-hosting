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
import time

class ClouderContainer(models.Model):
    """
    Add methods to manage the gitlab specificities.
    """

    _inherit = 'clouder.container'

    @property
    def base_backup_container(self):
        res = super(ClouderContainer, self).base_backup_container
        if self.application_id.type_id.name == 'gitlab':
            res = self.childs['exec']
        return res

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'gitlab':
            database_file = '/opt/gitlab/config/database.yml'
            secrets_file = '/opt/gitlab/config/secrets.yml'
            if self.application_id.code == 'data':
                self.execute(['sed', '-i', 's/DB_SERVER/' +
                             self.db_server + '/g',
                             database_file])
                self.execute([
                    'sed', '-i',
                    's/DB_USER/' + self.db_user + '/g',
                    database_file])
                self.execute([
                    'sed', '-i', 's/DB_PASSWORD/' +
                    self.db_password + '/g',
                    database_file])
                self.execute([
                    'sed', '-i', 's/SECRET/' +
                    self.options['secret']['value'] + '/g',
                    secrets_file])
            if self.application_id.code == 'exec':
                self.execute(['bundle', 'exec', 'rake', 'gitlab:shell:install', 'REDIS_URL=unix:/var/run/redis/redis.sock', 'RAILS_ENV=production'], path='/opt/gitlab/files')
                self.execute(['bundle', 'exec', 'rake', 'assets:precompile', 'RAILS_ENV=production'], path='/opt/gitlab/files')

class ClouderBase(models.Model):
    """
    Add methods to manage the odoo base specificities.
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_post(self):
        """
        Update gitlab configuration.
        """
        res = super(ClouderBase, self).deploy_post()
        if self.application_id.type_id.name == 'gitlab':
            self.container_id.database.execute([
                'psql', '-d', 'template1', '-c', '"CREATE EXTENSION IF NOT EXISTS pg_trgm;"'
            ], username='postgres')
            self.container_id.childs['data'].execute(['sed', '-i', '"s/database: [0-9a-z_]*/database: ' + self.fullname_ + '/g"',
                          '/opt/gitlab/config/database.yml'])
            self.container_id.childs['exec'].execute(['yes', 'yes', '|', 'bundle', 'exec', 'rake', 'gitlab:setup', 'RAILS_ENV=production', 'GITLAB_ROOT_PASSWORD=' + self.admin_password, 'GITLAB_ROOT_EMAIL=' + self.admin_email], path='/opt/gitlab/files')
            self.container_id.childs['exec'].execute(['bundle', 'exec', 'rake', 'assets:precompile', 'RAILS_ENV=production'], path='/opt/gitlab/files')
            self.container_id.childs['exec'].execute(['cp', '/opt/gitlab/files/lib/support/nginx/gitlab', '/etc/nginx/sites-available/' + self.fullname])
            self.container_id.childs['exec'].execute(['sed', '-i', '"s/server_name [A-Z0-9a-z_.]*;/server_name ' + self.fulldomain + ';/g"', '/etc/nginx/sites-available/' + self.fullname])
            self.container_id.childs['exec'].execute(['sed', '-i', '"s/\/home\/git\/gitlab/\/opt\/gitlab\/files/g"', '/etc/nginx/sites-available/' + self.fullname])
            self.container_id.childs['exec'].execute(['ln', '-s', '/etc/nginx/sites-available/' + self.fullname, '/etc/nginx/sites-enabled/' + self.fullname])
            self.container_id.childs['exec'].start()
        return res

    @api.multi
    def purge_post(self):
        """
        """
        res = super(ClouderBase, self).purge_post()
        if self.application_id.type_id.name == 'gitlab':
            self.container_id.childs['exec'].execute(['rm', '/etc/nginx/sites-enabled/' + self.fullname])
            self.container_id.childs['exec'].execute(['rm', '/etc/nginx/sites-available/' + self.fullname])
            self.container_id.childs['exec'].start()
        return res
