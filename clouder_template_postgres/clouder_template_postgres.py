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


class ClouderContainer(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.container'

    @property
    def db_type(self):
        db_type = super(ClouderContainer, self).db_type
        if db_type == 'postgres':
            db_type = 'pgsql'
        return db_type

    @api.multi
    def deploy_post(self):
        """
        Allow ip from options.
        """
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'postgres':
            self.execute([
                'echo "host all  all    ' +
                self.options['network']['value'] +
                ' md5" >> /etc/postgresql/' +
                self.application_id.current_version + '/main/pg_hba.conf'])
            self.execute([
                'echo "listen_addresses=\'' +
                self.options['listen']['value'] + '\'" >> /etc/postgresql/' +
                self.application_id.current_version + '/main/postgresql.conf'])

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
        if self.name.name.code == 'postgres':
            self.log('Creating database user')

            container = self.container_id
            container.database.execute([
                'psql', '-c', '"CREATE USER ' + container.db_user +
                ' WITH PASSWORD \'' + container.db_password + '\' CREATEDB;"'
            ], username='postgres')

            username=container.application_id.type_id.system_user
            home = '/home/' + username
            container.execute([
                'sed', '-i', '"/:*:' + container.db_user + ':/d" ' + home + '/.pgpass'], username=username)
            container.execute([
                'echo "' + container.db_server + ':5432:*:' +
                container.db_user + ':' + container.db_password +
                '" >> ' + home + '/.pgpass'], username=username)
            container.execute(['chmod', '700', home + '/.pgpass'], username=username)

            self.log('Database user created')

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderContainerLink, self).purge_link()
        if self.name.name.code == 'postgres':
            container = self.container_id
            container.database.execute( [
                'psql', '-c', '"DROP USER ' + container.db_user + ';"'], username='postgres')
            username=container.application_id.type_id.system_user
            container.execute([
                'sed', '-i', '"/:*:' + container.db_user + ':/d" /home/' + username + '/.pgpass'], username=username)

class ClouderBase(models.Model):
    """
    Add methods to manage the postgres base specificities.
    """

    _inherit = 'clouder.base'

    @api.multi
    def deploy_database(self):
        """
        Create the database with odoo functions.
        """

        if self.container_id.db_type == 'pgsql':
            for key, database in self.databases.iteritems():
                self.container_id.execute(['createdb', '-h',
                                   self.container_id.db_server, '-U',
                                   self.container_id.db_user, database])

        return super(ClouderBase, self).deploy_database()


    @api.multi
    def purge_database(self):
        """
        Purge the database.
        """
        if self.container_id.db_type == 'pgsql':
            for key, database in self.databases.iteritems():
                self.container_id.database.execute([
                    'psql', '-c',
                    '"update pg_database set datallowconn = \'false\' '
                    'where datname = \'' + database + '\'; '
                    'SELECT pg_terminate_backend(pid) '
                    'FROM pg_stat_activity WHERE datname = \''
                    + database + '\';"'
                ], username='postgres')
                self.container_id.database.execute(['dropdb', database], username='postgres')
        return super(ClouderBase, self).purge_database()


class ClouderSave(models.Model):


    _inherit = 'clouder.save'

    @api.multi
    def save_database(self):
        """

        :return:
        """

        res = super(ClouderSave, self).save_database()

        if self.base_id.container_id.db_type == 'pgsql':
            container = self.base_id.container_id.base_backup_container
            for key, database in self.base_id.databases.iteritems():
                container.execute([
                    'pg_dump', '-O', ''
                    '-h', self.container_id.db_server,
                    '-U', self.container_id.db_user, database,
                    '>', '/base-backup/' + self.name + '/' +
                    database + '.dump'], username=self.base_id.application_id.type_id.system_user)
        return res

    @api.multi
    def restore_database(self, base):
        super(ClouderSave, self).restore_database(base)
        if base.container_id.db_type == 'pgsql':
            container = base.container_id.base_backup_container
            for key, database in base.databases.iteritems():
                container.execute(['createdb', '-h',
                                   base.container_id.db_server, '-U',
                                   base.container_id.db_user,
                                   base.fullname_])
                container.execute(['cat',
                                   '/base-backup/restore-' + self.name + '/' + self.base_dumpfile,
                                   '|', 'psql', '-q', '-h',
                                   base.container_id.db_server, '-U',
                                   base.container_id.db_user,
                                   base.fullname_])
