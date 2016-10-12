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
import openerp.addons.clouder.model as model


class ClouderApplicationTypeOption(models.Model):
    """
    """

    _inherit = 'clouder.application.type.option'

    @api.multi
    def generate_default(self):
        res = super(ClouderApplicationTypeOption, self).generate_default()
        if self.name == 'root_password' \
                and self.application_type_id.name == 'mysql':
            res = model.generate_random_password(20)
        return res


class ClouderContainer(models.Model):
    """
    Add methods to manage the mysql container specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def get_container_res(self):
        res = super(ClouderContainer, self).get_container_res()
        if self.image_id.type_id.name == 'mysql':
            res['environment'].update({
                'MYSQL_ROOT_PASSWORD':
                    self.parent_id.container_id
                        .options['root_password']['value']})
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

        if self.application_id.type_id.name == 'mysql' \
                and self.application_id.check_tags(['exec']):

            self.start()

            self.execute([
                'sed', '-i', '"/bind-address/d"', '/etc/mysql/my.cnf'])
            password = \
                self.parent_id.container_id.options['root_password']['value']
            self.execute(['mysqladmin', '-u', 'root', 'password', password])

            # Granting network permissions
            self.execute([
                'mysql',
                '--user=root',
                '--password=\''+password+'\'',
                '-e',
                '"GRANT ALL PRIVILEGES ON *.* TO \'root\'@\'%\' '
                'IDENTIFIED BY \''+password+'\'"'
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
        if self.name.type_id.name == 'mysql' \
                and self.container_id.application_id.check_tags(['data']):
            self.log('Creating database user')

            self.container_id.database.execute([
                "mysql -u root -p'" +
                self.container_id.database.root_password +
                "' -se \"create user '" + self.container_id.db_user +
                "' identified by '" + self.container_id.db_password + "';\""])

            self.log('Database user created')

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderContainerLink, self).purge_link()
        if self.name.type_id.name == 'mysql' \
                and self.container_id.application_id.check_tags(['data']):
            self.container_id.database.execute([
                "mysql -u root -p'" +
                self.container_id.database.root_password +
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
                    "mysql -u root -p'" +
                    self.container_id.database.root_password +
                    "' -se \"create database " + database + ";\""
                ])
                self.container_id.database.execute([
                    "mysql -u root -p'" +
                    self.container_id.database.root_password +
                    "' -se \"grant all on " + database +
                    ".* to '" + self.container_id.db_user + "';\""
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
                    "mysql -u root -p'" +
                    self.container_id.database.root_password +
                    "' -se \"drop database " + database + ";\""
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
