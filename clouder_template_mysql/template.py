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
import openerp.addons.clouder.model as clouder_model


class ClouderContainer(models.Model):
    """
    Add methods to manage the mysql container specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def hook_deploy_source(self):
        res = super(ClouderContainer, self).hook_deploy_source()
        if self.application_id.type_id.name == 'mysql':
            res = " -e MYSQL_ROOT_PASSWORD={0} ".format(self.options['root_password']['value']) + res
        return res

    @property
    def db_user(self):
        """
        Property returning the database user of the service.
        """
        db_user = super(ClouderContainer, self).db_user
        if self.db_type == 'mysql':
            db_user = self.name[:14]
            db_user = db_user.replace('-', '_')
        return db_user

    @api.multi
    def deploy_post(self):
        """
        Updates the root password after deployment.
        Updates auth methods to allow network connections
        """
        super(ClouderContainer, self).deploy_post()

        if self.application_id.type_id.name == 'mysql':

            self.start()

            self.execute(['sed', '-i', '"/bind-address/d"', '/etc/mysql/my.cnf'])
            if self.options['root_password']['value']:
                password = self.options['root_password']['value']
            else:
                password = clouder_model.generate_random_password(20)
                option_obj = self.env['clouder.container.option']
                options = option_obj.search([('container_id', '=', self),
                                             ('name', '=', 'root_password')])
                if options:
                    options.value = password
                else:
                    type_option_obj = self.env[
                        'clouder.application.type.option']
                    type_options = type_option_obj.search(
                        [('apptype_id.name', '=', 'mysql'),
                         ('name', '=', 'root_password')])
                    if type_options:
                        option_obj.create({'container_id': self,
                                           'name': type_options[0],
                                           'value': password})
            self.execute(['mysqladmin', '-u', 'root', 'password', password])

            # Granting network permissions
            self.execute([
                'mysql',
                '--user=root',
                '--password=\''+password+'\'',
                '-e',
                '"GRANT ALL PRIVILEGES ON *.* TO \'root\'@\'%\' IDENTIFIED BY \''+password+'\'"'
            ])


class ClouderContainerLink(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):
        """
        Deploy the configuration file to watch the container.
        """
        super(ClouderContainerLink, self).deploy_link()
        if self.name.type_id.name == 'mysql':
            self.log('Creating database user')

            self.container_id.database.execute([
                "mysql -u root -p'" + self.container_id.database.root_password +
                "' -se \"create user '" + self.container_id.db_user +
                "' identified by '" + self.container_id.db_password + "';\""])

            self.log('Database user created')

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderContainerLink, self).purge_link()
        if self.name.type_id.name == 'mysql':
            self.container_id.database.execute([
                "mysql -u root -p'" + self.container_id.database.root_password +
                "' -se \"drop user " + self. container_id.db_user + ";\""])


class ClouderBase(models.Model):
    """
    Add methods to manage the odoo base specificities.
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_database(self):
        """
        Create the database with odoo functions.
        """

        if self.container_id.db_type == 'mysql':
            for key, database in self.databases.iteritems():
                self.container_id.database.execute([
                    "mysql -u root -p'"
                    + self.container_id.database.root_password
                    + "' -se \"create database " + database + ";\""
                ])
                self.container_id.database.execute([
                    "mysql -u root -p'"
                    + self.container_id.database.root_password
                    + "' -se \"grant all on " + database
                    + ".* to '" + self.container_id.db_user + "';\""
                ])
        return super(ClouderBase, self).deploy_database()

    @api.multi
    def purge_database(self):
        """
        Purge the database.
        """
        if self.container_id.db_type == 'mysql':
            for key, database in self.databases.iteritems():
                self.container_id.database.execute([
                    "mysql -u root -p'"
                    + self.container_id.database.root_password
                    + "' -se \"drop database " + database + ";\""
                ])
        return super(ClouderBase, self).purge_database()


class ClouderSave(models.Model):

    _inherit = 'clouder.save'

    @api.multi
    def save_database(self):
        """

        :return:
        """

        res = super(ClouderSave, self).save_database()

        if self.base_id.container_id.db_type == 'mysql':
            container = self.base_id.container_id
            for key, database in self.base_id.databases.iteritems():
                container.execute([
                    'mysqldump',
                    '-h', container.db_server,
                    '-u', container.db_user,
                    '-p' + container.db_password,
                    database, '>', '/base-backup/' + self.name +
                    '/' + self.base_dumpfile],
                    username=self.base_id.application_id.type_id.system_user)
        return res

    @api.multi
    def restore_database(self, base):
        super(ClouderSave, self).restore_database(base)
        if base.container_id.db_type == 'mysql':

            for key, database in base.databases.iteritems():
                db = base.container_id.database
                db.execute([
                    "mysql -u root -p'" +
                    database.root_password +
                    "' -se \"create database " + database + ";\""])
                db.execute([
                    "mysql -u root -p'" +
                    database.root_password +
                    "' -se \"grant all on " + database + ".* to '" +
                    base.conteneur_id.db_user + "';\""])
                base.conteneur_id.execute([
                    'mysql', '-h', base.conteneur_id.db_server, '-u',
                    base.conteneur_id.db_user,
                    '-p' + base.conteneur_id.db_password, database,
                    '<', '/base-backup/' + self.name + '/' +
                    self.base_dumpfile])
