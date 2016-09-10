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

from openerp import modules
from openerp import models, api


class ClouderContainer(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def send_drush_file(self):
        self.send(
            modules.get_module_path('clouder_template_drupal') +
            '/res/drush.make', '/var/www/drush.make',
            username='www-data')

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()


        if self.application_id.type_id.name == 'drupal' and self.application_id.check_tags(['exec']):
            self.send_drush_file()
            self.execute(['drush', 'make',
                          '/var/www/drush.make', '/var/www/drupal'], username='www-data')
            # self.execute(['mv', self.full_archivepath + '/sites',
            #                    self.full_archivepath + '/sites-template'])
            # self.execute(['ln', '-s', '../sites',
            #                    self.full_archivepath + '/sites'])
            #
            # self.execute(['cp', '-R',
            #                    self.full_localpath_files + '/sites-template',
            #                    self.full_localpath + '/sites'])


class ClouderBase(models.Model):
    """
    Add methods to manage the drupal base specificities.
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_build(self):
        """
        Build the drupal by calling drush site-install, and installing the
        specified modules and themes.
        """
        from openerp import modules
        res = super(ClouderBase, self).deploy_build()
        if self.application_id.type_id.name == 'drupal':
            config_file = '/etc/nginx/sites-available/' + self.fullname
            self.container_id.send(modules.get_module_path('clouder_template_drupal') +
                      '/res/nginx.config', config_file)
            self.container_id.execute(['sed', '-i', '"s/BASE/' + self.name + '/g"',
                               config_file])
            self.container_id.execute(['sed', '-i',
                               '"s/DOMAIN/' + self.domain_id.name + '/g"',
                               config_file])
            self.container_id.execute(['ln', '-s',
                               '/etc/nginx/sites-available/' + self.fullname,
                               '/etc/nginx/sites-enabled/' + self.fullname])
            self.container_id.execute(['/etc/init.d/nginx', 'reload'])
            #
            self.container_id.execute(['drush', '-y', 'si',
                               '--db-url=' + self.container_id.db_type +
                               '://' + self.container_id.db_user + ':' +
                               self.container_id.db_password + '@' +
                               self.container_id.db_server + '/' +
                               self.fullname_,
                               '--account-mail=' + self.admin_email,
                               '--account-name=' + self.admin_name,
                               '--account-pass=' + self.admin_password,
                               '--sites-subdir=' + self.fulldomain,
                               'minimal'],
                         path='/var/www/drupal', username='www-data')

            if self.application_id.options['install_modules']['value']:
                modules = self.application_id.options['install_modules'][
                    'value'].split(',')
                for module in modules:
                    self.container_id.execute(['drush', '-y', 'en', module],
                                 path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')
            if self.application_id.options['theme']['value']:
                theme = self.application_id.options['theme']['value']
                self.container_id.execute(['drush', '-y', 'pm-enable', theme],
                             path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')
                self.container_id.execute(['drush', 'vset', '--yes', '--exact',
                                   'theme_default', theme],
                             path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')

        return res

    # post restore
    #     ssh $system_user@$server << EOF
    #       mkdir $instances_path/$instance/sites/$clouder.$domain
    #       cp -r $instances_path/$instance/$db_type/sites/*
    # $instances_path/$instance/sites/$clouder.$domain/
    #       cd $instances_path/$instance/sites/$clouder.$domain
    #       sed -i "s/'database' => '[#a-z0-9_!]*'/'database' =>
    # '$fullname_underscore'/g" $instances_path/$instance/sites/
    # $clouder.$domain/settings.php
    #       sed -i "s/'username' => '[#a-z0-9_!]*'/'username' => '
    # $db_user'/g" $instances_path/$instance/sites/
    # $clouder.$domain/settings.php
    #       sed -i "s/'password' => '[#a-z0-9_!]*'/'password' =>
    # '$database_passwpord'/g" $instances_path/$instance/
    # sites/$clouder.$domain/settings.php
    #       sed -i "s/'host' => '[0-9.]*'/'host' => '$database_server'/g"
    # $instances_path/$instance/sites/$clouder.$domain/settings.php
    #       pwd
    #       echo Title $title
    #       drush vset --yes --exact site_name $title
    #       drush user-password $admin_user --password=$admin_password
    # EOF
    #

    @api.multi
    def deploy_post(self):
        """
        Set the drupal title.
        """
        res = super(ClouderBase, self).deploy_post()
        if self.application_id.type_id.name == 'drupal':
            self.container_id.execute(['drush', 'vset', '--yes',
                               '--exact', 'site_name', self.title],
                         path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')
        return res

    @api.multi
    def deploy_create_poweruser(self):
        """
        Create the poweruser.
        """
        res = super(ClouderBase, self).deploy_create_poweruser()
        if self.application_id.type_id.name == 'drupal':
            self.container_id.execute(['drush', 'user-create', self.poweruser_name,
                               '--password=' + self.poweruser_password,
                               '--mail=' + self.poweruser_email],
                         path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')
            if self.application_id.options['poweruser_group']['value']:
                self.container_id.execute(['drush', 'user-add-role',
                                   self.application_id.options[
                                       'poweruser_group']['value'],
                                   self.poweruser_name],
                             path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')
        return res

    @api.multi
    def deploy_test(self):
        """
        Install the test modules.
        """
        res = super(ClouderBase, self).deploy_test()
        if self.application_id.type_id.name == 'drupal':
            if self.application_id.options['test_install_modules']['value']:
                modules = \
                    self.application_id.options['test_install_modules'][
                        'value'].split(',')
                for module in modules:
                    self.container_id.execute(['drush', '-y', 'en', module],
                                 path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')
        return res

    @api.multi
    def post_reset(self):
        """
        Get the sites folder from parent base.
        """
        res = super(ClouderBase, self).post_reset()
        # if self.application_id.type_id.name == 'drupal':
        #     ssh = self.connect(
        #         self.service_id.container_id.fullname,
        #         username=self.application_id.type_id.system_user)
        #     self.container_id.execute(['cp', '-R',
        #                        self.parent_id.service_id.full_localpath +
        #                        '/sites/' + self.parent_id.fulldomain,
        #                        self.service_id.full_localpath_files +
        #                        '/sites/' + self.fulldomain], username='www-data')
        #     ssh.close()

        return res

    @api.multi
    def update_base(self):
        """
        Trigger an updatedb.
        """
        res = super(ClouderBase, self).update_base()
        if self.application_id.type_id.name == 'drupal':
            self.execute(['drush', 'updatedb'],
                         path='/var/www/drupal/sites/' + self.fulldomain, username='www-data')
        return res

    @api.multi
    def purge_post(self):
        """
        Purge the sites folder and nginx configuration.
        """
        super(ClouderBase, self).purge_post()
        if self.application_id.type_id.name == 'drupal':
            self.container_id.execute(['rm', '-rf',
                               '/var/www/sites/' + self.fulldomain])
            self.container_id.execute(['rm', '-rf',
                               '/etc/nginx/sites-enabled/' + self.fullname])
            self.container_id.execute(['rm', '-rf',
                               '/etc/nginx/sites-available/' +
                               self.fullname])
            self.container_id.execute(['/etc/init.d/nginx', 'reload'])


class ClouderSave(models.Model):
    """
    Add methods to manage the drupal save specificities.
    """

    _inherit = 'clouder.save'

    @api.multi
    def deploy_base(self):
        """
        Backup the sites folder.
        """
        res = super(ClouderSave, self).deploy_base()
        if self.base_id.application_id.type_id.name == 'drupal':
            # self.execute(ssh, ['drush', 'archive-dump', self.fullname_,
            #  '--destination=/base-backup/' + vals['saverepo_name'] +
            # 'tar.gz'])
            self.container_id.execute(['cp', '-R',
                               '/var/www/drupal/sites/' + self.base_id.fulldomain,
                               '/base-backup/' + self.fullname + '/site'], username='www-data')
        return res

    @api.multi
    def restore_base(self, base):
        """
        Restore the sites folder.
        """
        res = super(ClouderSave, self).restore_base(base)
        if self.base_id.application_id.type_id.name == 'drupal':
            self.container_id.execute(['rm', '-rf',
                               '/var/www/drupal/sites/' + self.base_id.fulldomain], username='www-data')
            self.container_id.execute(['cp', '-R',
                               '/base-backup/' + self.fullname + '/site',
                               '/var/www/drupal/sites/' + self.base_id.fulldomain], username='www-data')
        return res


class ClouderBaseLink(models.Model):
    """
    Add methods to manage the drupal base link specificities.
    """

    _inherit = 'clouder.base.link'

    # @api.multi
    # def deploy_piwik(self, piwik_id):
    #     """
    #     Add the piwik configuration on drupal.
    #
    #     :param piwik_id: The is of the website in piwik.
    #     """
    #     res = super(ClouderBaseLink, self).deploy_piwik(piwik_id)
    #     if self.name.name.code == 'piwik' \
    #             and self.base_id.application_id.type_id.name == 'drupal':
    #         ssh = self.connect(self.container_id.fullname)
    #         self.execute(ssh,
    #                      ['drush', 'variable-set', 'piwik_site_id', piwik_id],
    #                      path=self.base_id.service_id.full_localpath_files +
    #                      '/sites/' + self.base_id.fulldomain)
    #         self.execute(ssh, ['drush', 'variable-set', 'piwik_url_http',
    #                            'http://' + self.target.fulldomain + '/'],
    #                      path=self.base_id.service_id.full_localpath_files +
    #                      '/sites/' + self.base_id.fulldomain)
    #         self.execute(ssh, ['drush', 'variable-set', 'piwik_url_https',
    #                            'https://' + self.target.fulldomain + '/'],
    #                      path=self.base_id.service_id.full_localpath_files +
    #                      '/sites/' + self.base_id.fulldomain)
    #         self.execute(ssh, ['drush', 'variable-set',
    #                            'piwik_privacy_donottrack', '0'],
    #                      path=self.base_id.service_id.full_localpath_files +
    #                      '/sites/' + self.base_id.fulldomain)
    #         ssh.close()
    #     return res
