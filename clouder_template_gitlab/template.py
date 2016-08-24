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
from datetime import datetime
from openerp.addons.clouder import model


class ClouderApplicationTypeOption(models.Model):
    """
    """

    _inherit = 'clouder.application.type.option'

    @api.multi
    def generate_default(self):
        res = super(ClouderApplicationTypeOption, self).generate_default()
        if self.name == 'token' and self.type_id.name == 'gitlab':
            res = model.generate_random_password(20)
        return res


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
                # self.execute(['sed', '-i', '"s/Port [0-9]*/Port ' + self.ports['ssh']['hostport'] + '/g"', '/etc/ssh/sshd_config'])
                self.execute(['sed', '-i', '"s/ssh_port: [0-9]*/ssh_port: ' + self.ports['ssh']['hostport'] + '/g"', '/opt/gitlab/config/gitlab.yml'])
                self.start()
                self.execute(['bundle', 'exec', 'rake', 'gitlab:shell:install', 'REDIS_URL=redis://redis:6379', 'RAILS_ENV=production'], path='/opt/gitlab/files', username='git')
                self.execute(['chown', '-R', 'git:git', '/home/git/'])
                self.execute(['bundle', 'exec', 'rake', 'assets:precompile', 'RAILS_ENV=production'], path='/opt/gitlab/files', username='git')
                self.execute(['cp', '/opt/gitlab/files/lib/support/init.d/gitlab', '/etc/init.d/gitlab'])

        if self.application_id.type_id.name == 'gitlabci':
            if self.application_id.code == 'exec':
                self.execute(['sed', '-i', '"s/concurrent = [0-9]*/concurrent = ' + self.options['concurrent']['value'] + '/g"',
                             '/etc/gitlab-runner/config.toml'])


class ClouderContainerLink(models.Model):
    """
    Add methods to manage the gitlab specificities.
    """

    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):
        """
        Configure gitlab ci
        """
        super(ClouderContainerLink, self).deploy_link()

        if self.name.name.code == 'gitlab' \
                and self.container_id.application_id.type_id.name == 'gitlabci':
            if self.target.base_ids:
                container = self.target.childs['data']
                base = self.target.base_ids[0]
                token = self.target.childs['exec'].execute(['psql', '-h', 'postgres', '-U',  container.db_user, '-tA', '-c', '"SELECT runners_registration_token FROM application_settings ORDER BY id desc LIMIT 1;"', base.fullname_])
                self.container_id.childs['exec'].execute([
                    'gitlab-runner', 'register', '-n',
                    '-u', 'https://' + base.fulldomain + '/ci',
                    '-r', token.replace('\n',''),
                    '--name', self.container_id.fullname,
                    '--executor', 'docker',
                    '--docker-image', 'clouder/clouder-base'
                ])
        elif self.name.name.code == 'gitlab':
            if self.target.base_ids:
                base = self.target.base_ids[0]
                flag = False
                groups = self.request('https://' + base.fulldomain + '/api/v3/groups', headers={'PRIVATE-TOKEN' :base.options['token']['value']}).json()
                for group in groups:
                    if group['path'] == self.container_id.environment_id.prefix:
                        group_id = group['id']
                        flag = True
                if not flag:
                    group = self.request('https://' + base.fulldomain + '/api/v3/groups', headers={'PRIVATE-TOKEN' :base.options['token']['value']}, method='post', data={'name': self.container_id.environment_id.name, 'path': self.container_id.environment_id.prefix})
                    group_id = group.json()['id']
                if self.request('https://' + base.fulldomain + '/api/v3/projects/' + self.container_id.environment_id.prefix + '%2F' + self.container_id.name, headers={'PRIVATE-TOKEN' :base.options['token']['value']}, params={'name': self.container_id.fullname}).status_code != 200:
                    project = self.request('https://' + base.fulldomain + '/api/v3/projects', headers={'PRIVATE-TOKEN' :base.options['token']['value']}, method='post', data={'name': self.container_id.name, 'namespace_id': group_id}).json()
                    with open(modules.get_module_path('clouder_template_' + self.container_id.application_id.type_id.name) +'/res/gitignore', 'rb') as file:
                        self.request('https://' + base.fulldomain + '/api/v3/projects/' + str(project['id']) + '/repository/files', headers={'PRIVATE-TOKEN' :base.options['token']['value']}, method='post', data={'file_path': '.gitignore', 'branch_name': 'master', 'commit_message': 'Add .gitignore', 'content': file.read()})
                    with open(modules.get_module_path('clouder_template_' + self.container_id.application_id.type_id.name) +'/res/Dockerfile', 'rb') as file:
                        self.request('https://' + base.fulldomain + '/api/v3/projects/' + str(project['id']) + '/repository/files', headers={'PRIVATE-TOKEN' :base.options['token']['value']}, method='post', data={'file_path': 'Dockerfile', 'branch_name': 'master', 'commit_message': 'Add Dockerfile', 'content': file.read()})
                    with open(modules.get_module_path('clouder_template_' + self.container_id.application_id.type_id.name) +'/res/gitlab-ci.yml', 'rb') as file:
                        self.request('https://' + base.fulldomain + '/api/v3/projects/' + str(project['id']) + '/repository/files', headers={'PRIVATE-TOKEN' :base.options['token']['value']}, method='post', data={'file_path': '.gitlab-ci.yml', 'branch_name': 'master', 'commit_message': 'Add .gitlab-ci.yml', 'content': file.read()})


    @api.multi
    def purge_link(self):
        """
        Purge gitlab ci configuration
        """
        super(ClouderContainerLink, self).purge_link()

        if self.name.name.code == 'gitlab' \
                and self.container_id.application_id.type_id.name == 'gitlabci':
            if self.target.base_ids and 'exec' in self.container_id.childs:
                container = self.container_id.childs['exec']
                base = self.target.base_ids[0]
                self.container_id.childs['exec'].execute([
                    'gitlab-runner', 'unregister',
                    '-u', 'https://' + base.fulldomain + '/ci',
                    '-n', self.container_id.fullname,
                ])


class ClouderBase(models.Model):
    """
    Add methods to manage the gitlab base specificities.
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_post(self):
        """
        Update gitlab configuration.
        """
        res = super(ClouderBase, self).deploy_post()
        if self.application_id.type_id.name == 'gitlab':
            self.container_id.childs['exec'].execute(['sed', '-i', '"s/https:\/\/[0-9a-z_-.]*\//https:\/\/' + self.fulldomain + '\//g"',
                          '/home/git/gitlab-shell/config.yml'])
            self.container_id.childs['exec'].execute(['sed', '-i', '"s/host: [A-Z0-9a-z_.]*/host: ' + self.fulldomain + '/g"', '/opt/gitlab/config/gitlab.yml'])
            self.container_id.database.execute([
                'psql', '-d', 'template1', '-c', '"CREATE EXTENSION IF NOT EXISTS pg_trgm;"'
            ], username='postgres')
            self.container_id.childs['data'].execute(['sed', '-i', '"s/database: [0-9a-z_]*/database: ' + self.fullname_ + '/g"',
                          '/opt/gitlab/config/database.yml'])
            self.container_id.childs['exec'].execute(['yes', 'yes', '|', 'bundle', 'exec', 'rake', 'gitlab:setup', 'RAILS_ENV=production', 'GITLAB_ROOT_PASSWORD=' + self.admin_password, 'GITLAB_ROOT_EMAIL=' + self.admin_email], path='/opt/gitlab/files', username='git')
            self.container_id.childs['exec'].execute(['bundle', 'exec', 'rake', 'assets:precompile', 'RAILS_ENV=production'], path='/opt/gitlab/files', username='git')
            container = self.container_id.childs['data']
            self.container_id.childs['exec'].execute(['psql', '-h', 'postgres', '-U',  self.container_id.db_user, '-c', '"INSERT INTO personal_access_tokens (user_id, token, name, created_at, updated_at) VALUES (1, \'' + self.options['token']['value'] + '\', \'Clouder\', \'' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\', \'' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\')"', self.fullname_])
            self.container_id.childs['exec'].execute(['mkdir', '-p', '/etc/nginx/ssl'])
            self.container_id.childs['exec'].execute([
                    'openssl', 'req', '-x509', '-nodes', '-days', '365',
                    '-newkey', 'rsa:2048', '-out', '/etc/nginx/ssl/gitlab.crt',
                    ' -keyout', '/etc/nginx/ssl/gitlab.key', '-subj', '"/C=FR/L=Paris/O=' +
                    self.domain_id.organisation +
                    '/CN=' + self.fulldomain + '"'])
            self.container_id.childs['exec'].execute(['cp', '/opt/gitlab/files/lib/support/nginx/gitlab-ssl', '/etc/nginx/sites-available/' + self.fullname])
            self.container_id.childs['exec'].execute(['sed', '-i', '"s/server_name [A-Z0-9a-z_.]*;/server_name ' + self.fulldomain + ';/g"', '/etc/nginx/sites-available/' + self.fullname])
            self.container_id.childs['exec'].execute(['sed', '-i', '"s/\/home\/git\/gitlab/\/opt\/gitlab\/files/g"', '/etc/nginx/sites-available/' + self.fullname])
            self.container_id.childs['exec'].execute(['ln', '-s', '/etc/nginx/sites-available/' + self.fullname, '/etc/nginx/sites-enabled/' + self.fullname])
            self.container_id.childs['exec'].execute(['chown', '-R', 'git:git', '/opt/gitlab'])
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


class ClouderBaseLink(models.Model):
    """
    Add methods to manage the proxy specificities.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_link(self):
        """
        Configure the proxy to redirect to the application port.
        """
        super(ClouderBaseLink, self).deploy_link()
        if self.name.name.code == 'proxy' and self.base_id.application_id.type_id.name == 'gitlab':
            key = self.target.execute(['cat', '/etc/ssl/private/' + self.base_id.fulldomain + '.key'])
            cert = self.target.execute(['cat', '/etc/ssl/certs/' + self.base_id.fulldomain + '.crt'])
            self.base_id.container_id.childs['exec'].execute([
                'echo', '"' + cert + '"', '>', '/etc/nginx/ssl/gitlab.crt'
            ])
            self.base_id.container_id.childs['exec'].execute([
                'echo', '"' + key + '"', '>', '/etc/nginx/ssl/gitlab.key'])
            self.base_id.container_id.childs['exec'].execute(['/etc/init.d/nginx', 'reload'])