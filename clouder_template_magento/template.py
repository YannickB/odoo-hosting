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


class ClouderContainer(models.Model):
    """
    Adds methods to manage magneto specificities.
    """

    _inherit = 'clouder.container'

    @property
    def base_backup_container(self):
        res = super(ClouderContainer, self).base_backup_container
        if self.application_id.type_id.name == 'magento':
            res = self.childs['exec']  # TODO: Ask what this does
        return res

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'magento':
            if self.application_id.code == 'exec':
                self.execute([
                    'cp',
                    '-r',
                    '/opt/magento/files/*',
                    '/opt/magento/exec'
                ])
                self.execute([
                    'cp',
                    '/opt/magento/config/config.xml',
                    '/opt/magento/exec/app/etc/'
                ])
                self.execute([
                    'chown',
                    '-R',
                    'www-data:www-data',
                    '/opt/magento'
                ])

            elif self.application_id.code == 'data':
                config_file = '/opt/magento/config/config.xml'

                self.execute([
                    'sed',
                    '-i',
                    '"s/CLOUDER_TEMPLATE_MAGENTO_DB_HOST/{replace}/g"'.format(
                        replace=self.db_server),
                    config_file
                ])
                self.execute([
                    'sed',
                    '-i',
                    '"s/CLOUDER_TEMPLATE_MAGENTO_DB_NAME/{replace}/g"'.format(
                        replace=self.name.replace('-', '_')
                    ),
                    config_file
                ])
                if 'locale' in self.options:
                    self.execute([
                        'sed',
                        '-i',
                        '"s/CLOUDER_TEMPLATE_MAGENTO_LOCALE/{replace}/g"'
                        .format(replace=self.options['locale']['value']),
                        config_file
                    ])
                if 'timezone' in self.options:
                    self.execute([
                        'sed',
                        '-i',
                        '"s/CLOUDER_TEMPLATE_MAGENTO_TZ/{replace}/g"'.format(
                            replace=self.options['timezone']['value']
                            .replace("/", r"\\\/")
                        ),
                        config_file
                    ])

    # TODO: re-add when a default value for admin-email has been automated
    # @api.multi
    # def deploy(self):
    #     super(ClouderContainer, self).deploy()
    #     if self.application_id.type_id.name == 'magento':
    #         if self.application_id.code == 'data':
    #             # Installing magento into the database once the link is done
    #             self.execute([
    #                 '/opt/magento/bin/magento',
    #                 'setup:install',
    #                 '--base-url={domain}:{port}/'.
    # format(domain=self.server_id.ip, port=self.ports['web']['hostport']),
    #                 '--db-host={db_host}'.format(dbhost=self.db_server),
    #                 '--db-name={dbname}'.
    # format(dbname=self.name.replace('-', '_')),
    #                 '--db-user={dbuser}'.format(db_user=self.db_user),
    #                 '--db-password={dbpass}'.
    # format(dbpass=self.options['db_password']['value']),
    #                 '--admin-firstname={adm_firstname}'.
    # format(adm_firstname=self.options['admin_firstname']['value']),
    #                 '--admin-lastname={adm_firstname}'.
    # format(adm_lastname=self.options['admin_lastname']['value']),
    #                 '--admin-email={adm_email}'.
    # format(adm_email=self.options['admin_email']['value']),
    #                 '--admin-user={adm_login}'.
    # format(adm_login=self.options['admin_user']['value']),
    #                 '--admin-password={adm_pass}'.
    # format(adm_pass=self.options['admin_password']['value']),
    #                 '--language={locale}'.
    # format(locale=self.options['locale']['value']),
    #                 '--currency={currency}'.
    # format(currency=self.options['currency']['value']),
    #                 '--timezone={tz}'.
    # format(tz=self.options['timezone']['value']),
    #                 '--use-rewrites={rewrite}'.
    # format(rewrite=self.options['use_rewrites']['value'])
    #             ])


class ClouderBase(models.Model):
    """
    Add methods to manage the magento base specificities.
    """

    _inherit = 'clouder.base'

    @property
    def magento_port(self):
        return self.container_id.childs['exec'] and \
            self.container_id.childs['exec'].ports['web']['hostport']

    @api.multi
    def deploy_database(self):
        """
        Create the magento database.
        """
        if self.application_id.type_id.name == 'magento':
            if self.build == 'build':
                dbname = self.container_id.name.replace('-', '_')
                # Create database
                self.container_id.database.execute([
                    "mysql -u root -p'" +
                    self.container_id.database.root_password +
                    "' -se \"create database " + dbname + ";\""
                ])
                # Create user
                self.container_id.database.execute([
                    "mysql -u root -p'" +
                    self.container_id.database.root_password +
                    "' -se \"create user '" + self.container_id.db_user +
                    "'@'%' IDENTIFIED BY '" +
                    self.container_id.childs['data']
                        .options['db_password']['value'] +
                    "';\""
                ])
                # Grant user rights on database
                self.container_id.database.execute([
                    "mysql -u root -p'" +
                    self.container_id.database.root_password +
                    "' -se \"grant all on " + dbname +
                    ".* to '" + self.container_id.db_user + "';\""
                ])
                # Make sure rights are applied
                self.container_id.database.execute([
                    "mysql -u root -p'" +
                    self.container_id.database.root_password +
                    "' -se \"FLUSH PRIVILEGES;\""
                ])

                return True
        return super(ClouderBase, self).deploy_database()
