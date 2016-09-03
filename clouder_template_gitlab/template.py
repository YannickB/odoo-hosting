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
        if self.name == 'token' and self.apptype_id.name == 'gitlab':
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


class ClouderContainerLink(models.Model):
    """
    Add methods to manage the gitlab specificities.
    """

    _inherit = 'clouder.container.link'

    @property
    def gitlab_url(self):
        return 'https://' + self.target.base_ids[0].fulldomain + '/api/v3'

    @property
    def gitlab_headers(self):
        return {'PRIVATE-TOKEN' : self.target.base_ids[0].options['token']['value']}


    def gitlab_ressource(self, type, name, project_id='', data={}):

        path = ''
        if type == 'group':
            path = '/groups'

        if type == 'group':
            flag = False
            data['path'] = name
            groups = self.request(self.gitlab_url + path, headers=self.gitlab_headers).json()
            for group in groups:
                if group['path'] == name:
                    res = group
                    flag = True
            if not flag:
                res = self.request(self.gitlab_url + path, headers=self.gitlab_headers, method='post', data=data).json()

        if type == 'variable':
            data['key'] = name
            if self.request(self.gitlab_url + '/projects/' + project_id + '/variables/' + name, headers=self.gitlab_headers).status_code != 200:
                res = self.request(self.gitlab_url + '/projects/' + project_id + '/variables', headers=self.gitlab_headers, method='post', data=data).json()
            else:
                res = self.request(self.gitlab_url + '/projects/' + project_id + '/variables/' + name, headers=self.gitlab_headers, method='put', data=data).json()

        if type == 'file':
            with open(modules.get_module_path('clouder_template_' + self.container_id.application_id.type_id.name) +'/res/' + name, 'rb') as file:
                res = self.request(self.gitlab_url + '/projects/' + project_id + '/repository/files', headers=self.gitlab_headers, method='post', data={'file_path': name, 'branch_name': 'master', 'commit_message': 'Add ' + name, 'content': file.read()})

        return res

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
                    '--docker-image', 'docker:latest',
                    # '--docker-privileged'
                    '--docker-volumes /var/run/docker.sock:/var/run/docker.sock'
                ])
                self.container_id.execute(['sed', '-i', '"s/concurrent = [0-9]*/concurrent = ' + self.container_id.options['concurrent']['value'] + '/g"',
                             '/etc/gitlab-runner/config.toml'])

        elif self.name.name.type_id.name == 'gitlab' and self.container_id.application_id.code == 'files':
            if self.target.base_ids:

                group_id = self.gitlab_ressource('group', self.container_id.environment_id.prefix, data={'name': self.container_id.environment_id.name})['id']

                project = self.request(self.gitlab_url + '/projects/' + self.container_id.environment_id.prefix + '%2F' + self.container_id.name, headers=self.gitlab_headers, params={'name': self.container_id.fullname})
                if project.status_code != 200:
                    project = self.request(self.gitlab_url + '/projects', headers=self.gitlab_headers, method='post', data={'name': self.container_id.name, 'namespace_id': group_id}).json()
                    self.gitlab_ressource('variable', 'REGISTRY_DOMAIN', project_id=str(project['id']), data={'value': self.container_id.links['registry'].target.base_ids[0].fulldomain + ':'  + self.container_id.links['registry'].target.ports['http']['hostport']})
                    self.gitlab_ressource('variable', 'REGISTRY_PASSWORD', project_id=str(project['id']), data={'value': self.container_id.options['registry_password']['value']})
                    self.gitlab_ressource('variable', 'SALT_DOMAIN', project_id=str(project['id']), data={'value': self.salt_master.server_id.name + ':'  + self.salt_master.ports['api']['hostport']})
                    self.gitlab_ressource('variable', 'PRODUCTION_SERVER', project_id=str(project['id']), data={'value': self.container_id.server_id.name})
                    self.gitlab_ressource('file', '.gitignore', project_id=str(project['id']))
                    self.gitlab_ressource('file', 'Dockerfile', project_id=str(project['id']))
                    self.gitlab_ressource('file', '.gitlab-ci.yml', project_id=str(project['id']))
                else:
                    project = project.json()
                    self.gitlab_ressource('variable', 'REGISTRY_DOMAIN', project_id=str(project['id']), data={'value': self.container_id.links['registry'].target.base_ids[0].fulldomain + ':'  + self.container_id.links['registry'].target.ports['http']['hostport']})
                    self.gitlab_ressource('variable', 'REGISTRY_PASSWORD', project_id=str(project['id']), data={'value': self.container_id.options['registry_password']['value']})

        if self.name.name.code == 'registry':
            if 'gitlab' in self.container_id.links:
                self.container_id.links['gitlab'].deploy_link()

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