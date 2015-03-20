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


from openerp import models, fields, api, _


class ClouderApplicationVersion(models.Model):
    _inherit = 'clouder.application.version'

    @api.multi
    def build_application(self):
        super(ClouderApplicationVersion, self).build_application()
        if self.application_id.code == 'gitlab':
            ssh = self.connect(self.archive_id.fullname)
            self.execute(ssh, ['git', 'clone',
                               'https://gitlab.com/gitlab-org/gitlab-ce.git',
                               '-b', '7-5-stable', 'gitlab'],
                         path=self.full_archivepath)
            self.execute(ssh, ['mv', 'gitlab/*', './'],
                         path=self.full_archivepath)
            self.execute(ssh, ['rm', '-r', 'gitlab'],
                         path=self.full_archivepath)
            ssh.close()

        return


class ClouderService(models.Model):
    _inherit = 'clouder.service'

    @api.multi
    def deploy_post_service(self):
        super(ClouderService, self).deploy_post_service()
        if self.application_id.code == 'gitlab':
            ssh = self.connect(self.container_id.fullname)
            self.execute(ssh, [
                'cp',
                self.full_localpath_files + '/config/gitlab.yml.example',
                self.full_localpath_files + '/config/gitlab.yml'])
            self.execute(ssh, ['chown', '-R', 'git',
                               self.full_localpath_files + '/log'])
            self.execute(ssh, ['chown', '-R', 'git',
                               self.full_localpath_files + '/tmp'])
            self.execute(ssh, ['chmod', '-R', 'u+rwX,go-w',
                               self.full_localpath_files + '/log'])
            self.execute(ssh, ['chmod', '-R', 'u+rwX,go-w',
                               self.full_localpath_files + '/tmp'])

            self.execute(ssh, ['mkdir',
                               self.full_localpath + '/gitlab-satellites'])
            self.execute(ssh, ['chmod', '-R', 'u+rwx,g=rx,o-rwx',
                               self.full_localpath + '/gitlab-satellites'])

            self.execute(ssh, ['chmod', '-R', 'u+rwX',
                               self.full_localpath_files + '/tmp/pids'])
            self.execute(ssh, ['chmod', '-R', 'u+rwX',
                               self.full_localpath_files + '/tmp/sockets'])
            self.execute(ssh, ['chmod', '-R', 'u+rwX',
                               self.full_localpath_files +
                               '/public/uploads'])

            self.execute(ssh, [
                'cp',
                self.full_localpath_files + '/config/unicorn.rb.example',
                self.full_localpath_files + '/config/unicorn.rb'])
            self.execute(ssh, [
                'cp',
                self.full_localpath_files +
                '/config/initializers/rack_attack.rb.example',
                self.full_localpath_files +
                '/config/initializers/rack_attack.rb'])
            self.execute(ssh, [
                'cp',
                self.full_localpath_files + '/config/resque.yml.example',
                self.full_localpath_files + '/config/resque.yml'])
            self.execute(ssh, ['chown', '-R', 'git', self.full_localpath])
            ssh.close()

        return


class ClouderBase(models.Model):
    _inherit = 'clouder.base'

    @api.multi
    def deploy_build(self):
        res = super(ClouderBase, self).deploy_build()
        if self.application_id.code == 'gitlab':
            ssh = self.connect(self.service_id.container_id.fullname)
            database_file = \
                self.service_id.full_localpath_files + '/config/database.yml'
            self.execute(ssh, ['cp', self.full_localpath_files +
                               '/config/database.yml.postgresql',
                               database_file])
            self.execute(ssh, [
                'sed', '-i',
                's/gitlabhq_production/' + self.fullname_ + '/g',
                database_file])
            self.execute(ssh, ['sed', '-i', 's/#\ username:\ git/username:\ ' +
                               self.service_id.db_user + '/g',
                               database_file])
            self.execute(ssh, ['sed', '-i', 's/#\ password:/password:\ ' +
                               self.service_id.database_password + '/g',
                               database_file])
            self.execute(ssh, ['sed', '-i', 's/#\ host:\ localhost/host:\ ' +
                               self.service_id.database_server + '/g',
                               database_file])
            ssh.close()
        return res

