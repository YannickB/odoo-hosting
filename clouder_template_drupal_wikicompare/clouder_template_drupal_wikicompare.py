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
from openerp import modules


class ClouderApplicationVersion(models.Model):
    _inherit = 'clouder.application.version'

    @api.multi
    def build_application(self):
        super(ClouderApplicationVersion, self).build_application()
        if self.application_id.type_id.name == 'drupal'\
                and self.application_id.code == 'wkc':
            ssh, sftp = self.connect(self.archive_id.fullname())
            self.send(sftp, modules.get_module_path('clouder_drupal') +
                      '/res/wikicompare.script',
                      self.full_archivepath() + '/wikicompare.script')
            self.send(sftp, modules.get_module_path('clouder_drupal') +
                      '/res/patch/revisioning_postgres.patch',
                      self.full_archivepath() + '/revisioning_postgres.patch')
            self.execute(ssh, ['patch', '-p0', '-d', self.full_archivepath() +
                               '/sites/all/modules/revisioning/', '<',
                               self.full_archivepath() +
                               '/revisioning_postgres.patch'])
            ssh.close(), sftp.close()


            #
            # if [[ $name == 'dev' ]]
            # then
            # patch -p0 -d $archive_path/$app/${app}-${name}/archive/sites/all/themes/wikicompare_theme/ < $openerp_path/clouder/clouder/apps/drupal/patch/dev_zen_rebuild_registry.patch
            # fi

        return


    @api.multi
    def get_current_version(self):
        return False


class ClouderBase(models.Model):
    _inherit = 'clouder.base'


    @api.multi
    def deploy_test(self):
        res = super(ClouderBase, self).deploy_test()
        if self.application_id.type_id.name == 'drupal' \
                and self.application_id.code == 'wkc':
            ssh, sftp = self.connect(
                self.service_id.container_id.fullname(),
                username=self.application_id.type_id.system_user)
            self.execute(ssh, ['drush', 'vset', '--yes', '--exact',
                               'wikicompare_test_platform', '1'],
                         path=self.service_id.full_localpath_files() +
                         '/sites/' + self.fulldomain())
            if self.poweruser_name and self.poweruser_email:
                self.execute(ssh, ['drush',
                                   self.service_id.full_localpath_files() +
                                   '/wikicompare.script',
                                   '--user=' + self.poweruser_name,
                                   'deploy_demo'],
                             path=self.service_id.full_localpath_files() +
                             '/sites/' + self.fulldomain())
            ssh.close(), sftp.close()
        return res


