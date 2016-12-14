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

from odoo import models, api


class ClouderContainer(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.service'

    @property
    def db_type(self):
        db_type = super(ClouderContainer, self).db_type
        if db_type == 'postgres':
            db_type = 'pgsql'
        return db_type

    # @api.multi
    # def deploy_post(self):
    #     """
    #     Allow ip from options.
    #     """
    #     super(ClouderContainer, self).deploy_post()
    #     if self.application_id.type_id.name == 'postgres'
    # and self.application_id.check_tags(['exec']):
    #         self.execute([
    #             'echo "host all  all    ' +
    #             self.options['network']['value'] +
    #             ' md5" >> /etc/postgresql/' +
    #             self.image_id.current_version + '/main/pg_hba.conf'])
    #         self.execute([
    #             'echo "listen_addresses=\'' +
    #             self.options['listen']['value'] + '\'" >> /etc/postgresql/' +
    #             self.image_id.current_version + '/main/postgresql.conf'])


class ClouderContainerLink(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.service.link'

    @api.multi
    def deploy_link(self):
        """
        Deploy the configuration file to watch the service.
        """
        super(ClouderContainerLink, self).deploy_link()
        if self.name.type_id.name == 'postgres' \
                and self.service_id.application_id.check_tags(['data']):
            self.log('Creating database user')

            service = self.service_id
            service.database.execute([
                'psql', '-c', '"CREATE USER ' + service.db_user +
                ' WITH PASSWORD \'$$$' + service.db_password +
                '$$$\' CREATEDB;"'
            ], username='postgres')

            username = service.application_id.type_id.system_user
#            home = '/home/' + username
            service.execute([
                'sed', '-i',
                '"/:*:' + service.db_user + ':/d" ' + '~/.pgpass'],
                username=username)
            service.execute([
                'echo "' + service.db_node + ':5432:*:' +
                service.db_user + ':$$$' + service.db_password +
                '$$$" >> ' + '~/.pgpass'], username=username)
            service.execute(['chmod', '700', '~/.pgpass'],
                            username=username)

            self.log('Database user created')

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderContainerLink, self).purge_link()
        if self.name.type_id.name == 'postgres' \
                and self.service_id.application_id.check_tags(['data']):
            service = self.service_id
            service.database.execute([
                'psql', '-c', '"DROP USER ' + service.db_user + ';"'],
                username='postgres')
            username = service.application_id.type_id.system_user
            service.execute([
                'sed', '-i',
                '"/:*:' + service.db_user +
                ':/d" ~/.pgpass'],
                username=username)


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

        if self.service_id.db_type == 'pgsql':
            for key, database in self.databases.iteritems():
                self.service_id.base_backup_service.execute([
                    'createdb', '-h', self.service_id.db_node, '-U',
                    self.service_id.db_user, database])

        return super(ClouderBase, self).deploy_database()

    @api.multi
    def purge_database(self):
        """
        Purge the database.
        """
        if self.service_id.db_type == 'pgsql':
            for key, database in self.databases.iteritems():
                self.service_id.database.execute([
                    'psql', '-c',
                    '"update pg_database set datallowconn = \'false\' '
                    'where datname = \'' + database + '\'; '
                    'SELECT pg_terminate_backend(pid) '
                    'FROM pg_stat_activity WHERE datname = \'' +
                    database + '\';"'
                ], username='postgres')
                self.service_id.database.execute(['dropdb', database],
                                                 username='postgres')
        return super(ClouderBase, self).purge_database()


class ClouderBackup(models.Model):

    _inherit = 'clouder.backup'

    @api.multi
    def backup_database(self):
        """

        :return:
        """

        res = super(ClouderBackup, self).backup_database()

        if self.base_id.service_id.db_type == 'pgsql':
            service = self.base_id.service_id.base_backup_service
            for key, database in self.base_id.databases.iteritems():
                service.execute([
                    'pg_dump', '-O', ''
                    '-h', self.service_id.db_node,
                    '-U', self.service_id.db_user, database,
                    '>', '/base-backup/' + self.name + '/' +
                    self.base_dumpfile],
                    username=self.base_id.application_id.type_id.system_user)
        return res

    @api.multi
    def restore_database(self, base):
        super(ClouderBackup, self).restore_database(base)
        if base.service_id.db_type == 'pgsql':
            service = base.service_id.base_backup_service
            for key, database in base.databases.iteritems():
                service.execute(['createdb', '-h',
                                 base.service_id.db_node, '-U',
                                 base.service_id.db_user,
                                 database])
                service.execute([
                    'cat',
                    '/base-backup/restore-' + self.name +
                    '/' + self.base_dumpfile,
                    '|', 'psql', '-q', '-h',
                    base.service_id.db_node, '-U',
                    base.service_id.db_user,
                    database])
