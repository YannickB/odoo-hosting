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


class ClouderContainer(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def send_drush_file(self):
        self.send(
            modules.get_module_path('clouder_template_drupal_wikicompare') +
            '/res/drush.make', '/var/www/drush.make',
            username='www-data')


    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()

        if self.application_id.type_id.name == 'drupal'\
                and self.application_id.code == 'wkc' and self.application_id.check_tags(['exec']):
            self.send(modules.get_module_path(
                'clouder_template_drupal_wikicompare') +
                '/res/wikicompare.script',
                '/var/www/drupal/wikicompare.script', username='www-data')
            self.send(modules.get_module_path(
                'clouder_template_drupal_wikicompare') +
                '/res/patch/revisioning_postgres.patch',
                '/var/www/drupal/revisioning_postgres.patch', username='www-data')
            self.execute(['patch', '-p0', '-d', '/var/www/drupal/sites/all/modules/revisioning/', '<',
                               '/var/www/drupal/revisioning_postgres.patch'], username='www-data')


class ClouderBase(models.Model):
    """
    Add methods to manage the wikicompare base specificities.
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_test(self):
        """
        Deploy the wikicompare test data.
        """
        res = super(ClouderBase, self).deploy_test()
        if self.application_id.type_id.name == 'drupal' \
                and self.application_id.code == 'wkc':
            self.container_id.execute(['drush', 'vset', '--yes', '--exact',
                               'wikicompare_test_platform', '1'],
                         path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')
            if self.poweruser_name and self.poweruser_email:
                self.container_id.execute(['drush',
                                   '/var/www/drupal/wikicompare.script',
                                   '--user=' + self.poweruser_name,
                                   'deploy_demo'],
                             path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')
        return res


