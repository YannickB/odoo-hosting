# -*- coding: utf-8 -*-
# #############################################################################
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


class ClouderApplicationVersion(models.Model):
    _inherit = 'clouder.application.version'

    @api.multi
    def build_application(self):
        super(ClouderApplicationVersion, self).build_application()
        if self.application_id.type_id.name == 'seafile':
            ssh = self.connect(self.archive_id.fullname)
            self.execute(ssh, [
                'wget', '-q',
                'https://bitbucket.org/haiwen/seafile/downloads'
                '/seafile-server_' + self.application_id.current_version +
                '_x86-64.tar.gz'],
                path=self.full_archivepath)
            self.execute(ssh, ['tar', '-xzf', 'seafile-server_*'],
                         path=self.full_archivepath)
            self.execute(ssh, [
                'mv', 'seafile-server-' + self.application_id.current_version +
                '/*', './'], path=self.full_archivepath)
            self.execute(ssh, ['rm', '-rf', './*.tar.gz'],
                         path=self.full_archivepath)
            self.execute(ssh, [
                'rm', '-rf',
                'seafile-server_' + self.application_id.current_version],
                path=self.full_archivepath)
            ssh.close()

        return


class ClouderBase(models.Model):
    _inherit = 'clouder.base'

    @api.multi
    def deploy_build(self):
        res = super(ClouderBase, self).deploy_build()
        if self.application_id.type_id.name == 'seafile':
            ssh = self.connect(
                self.service_id.container_id.fullname,
                username=self.application_id.type_id.system_user)
            install_args = [
                '\n', self.title + '\n', self.fulldomain + '\n', '\n', '\n',
                '\n', '\n', '2\n', 'mysql\n', '\n',
                self.service_id.db_user + '\n',
                self.service_id.database_password + '\n',
                self.databases['ccnet'] + '\n',
                self.databases['seafile'] + '\n',
                self.databases['seahub'] + '\n', '\n']
            seahub_args = [self.admin_email + '\n',
                           self.admin_password + '\n',
                           self.admin_password + '\n']
            if not self.options['manual_install']['value']:
                #Be cautious, the install may crash because of the server name (title). Use only alphanumeric, less than 15 letter without space
                self.execute(ssh, ['./setup-seafile-mysql.sh'],
                             stdin_arg=install_args,
                             path=self.service_id.full_localpath_files)

                self.execute(ssh, [
                    self.service_id.full_localpath_files + '/seafile.sh',
                    'start'])

                self.execute(ssh, [
                    self.service_id.full_localpath_files + '/seahub.sh',
                    'start'], stdin_arg=seahub_args)
            else:
                for arg in install_args:
                    self.log(arg)
                for arg in seahub_args:
                    self.log(arg)

        return res


    @api.multi
    def deploy_post(self):
        res = super(ClouderBase, self).deploy_post()
        if self.application_id.type_id.name == 'seafile':
            ssh = self.connect(
                self.service_id.container_id.fullname,
                username=self.application_id.type_id.system_user)
            self.execute(ssh, [
                'echo "[program:' + self.fullname +
                '-seafile]" >> /opt/seafile/supervisor.conf'])
            self.execute(ssh, [
                'echo "command=su seafile -c \'' +
                self.service_id.full_localpath_files +
                '/seafile.sh start\'" >> /opt/seafile/supervisor.conf'])
            self.execute(ssh, [
                'echo "[program:' + self.unifullname+
                '-seahub]" >> /opt/seafile/supervisor.conf'])
            self.execute(ssh, [
                'echo "command=su seafile -c \'rm ' +
                self.service_id.full_localpath_files +
                '/runtime/seahub.pid; ' +
                self.service_id.full_localpath_files +
                '/seahub.sh start\'" >> /opt/seafile/supervisor.conf'])

            ssh.close()
        return res

    @api.multi
    def purge_post(self):
        super(ClouderBase, self).purge_post()
        if self.application_id.type_id.name == 'seafile':
            ssh = self.connect(
                self.service_id.container_id.fullname,
                username=self.application_id.type_id.system_user)
            self.execute(ssh, [
                'sed', '-i',
                '"/program:' + self.fullname + '-seafile/d"',
                '/opt/seafile/supervisor.conf'])
            self.execute(ssh, [
                'sed', '-i',
                '"/' + self.service_id.full_localpath_files\
                         .replace('/', '\/') + '\/seafile.sh/d"',
                '/opt/seafile/supervisor.conf'])
            self.execute(ssh, [
                'sed', '-i',
                '"/program:' + self.unique_name() + '-seahub/d"',
                '/opt/seafile/supervisor.conf'])
            self.execute(ssh, [
                'sed', '-i',
                '"/' + self.service_id.full_localpath_files\
                         .replace('/', '\/') + '\/seahub.sh/d"',
                '/opt/seafile/supervisor.conf'])
            ssh.close()

        # class CloudeSaveSave(models.Model):
        #     _inherit = 'clouder.save.save'

        # @api.multi
        # def deploy_base(self, cr, uid, vals, context=None):
        #     res = super(clouder_save_save, self).deploy_base(cr, uid, vals, context)
        #     context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        #     if vals['apptype_name'] == 'drupal':
        #         ssh = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
        #         execute.execute(ssh, ['cp', '-R', vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'], '/base-backup/' + vals['saverepo_name'] + '/site'], context)
        #         ssh.close()
        #         sftp.close()
        #     return
        #
        # @api.multi
        # def restore_base(self, cr, uid, vals, context=None):
        #     res = super(clouder_save_save, self).restore_base(cr, uid, vals, context)
        #     context.update({'clouder-self': self, 'clouder-cr': cr, 'clouder-uid': uid})
        #     if vals['apptype_name'] == 'drupal':
        #         ssh = execute.connect(vals['container_fullname'], username=vals['apptype_system_user'], context=context)
        #         execute.execute(ssh, ['rm', '-rf', vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain']], context)
        #         execute.execute(ssh, ['cp', '-R', '/base-backup/' + vals['saverepo_name'] + '/site', vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain']], context)
        #         ssh.close()
        #         sftp.close()
        #     return

