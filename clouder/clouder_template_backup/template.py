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
    Add a property.
    """

    _inherit = 'clouder.container'

    @property
    def backup_method(self):
        """
        Property returning the backup method of the backup container.
        """
        backup_method = False
        if self.application_id.code == 'backup-sim':
            backup_method = 'simple'
        if self.application_id.code == 'backup-bup':
            backup_method = 'bup'

        return backup_method


class ClouderContainerLink(models.Model):
    """
    Add the method to manage transfers to the distant containers.
    """
    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):
        """
        Upload the whole backups to a distant container.
        """
        if self.name.type_id.name == 'backup-upload' \
                and self.container_id.application_id.type_id.name == 'backup':
            filegz = self.container_id.fullname + '.tar.gz'
            file_destination = '/opt/upload/' + filegz
            tmp_file = '/tmp/backup-upload/' + filegz
       
            container = self.container_id
            container.execute(['mkdir', '-p', '/tmp/backup-upload'])
            container.execute(['tar', 'czf', tmp_file, '-C /opt/backup', '.'])

            container.send(
                self.home_directory + '/.ssh/config',
                '/home/backup/.ssh/config', username='backup')
            container.send(
                self.home_directory + '/.ssh/keys/' +
                self.target.server_id.fulldomain + '.pub',
                '/home/backup/.ssh/keys/' +
                self.target.server_id.fulldomain + '.pub',
                username='backup')
            container.send(
                self.home_directory + '/.ssh/keys/' +
                self.target.server_id.fulldomain,
                '/home/backup/.ssh/keys/' +
                self.target.server_id.fulldomain, username='backup')
            container.execute([
                'chmod', '-R', '700', '/home/backup/.ssh'], username='backup')

            self.target.server_id.execute(['mkdir', '-p', '/tmp/backup-upload'])
            container.execute([
                'rsync', "-e 'ssh -o StrictHostKeyChecking=no'", '-ra',
                tmp_file, self.target.server_id.fulldomain + ':' + tmp_file],
                username='backup')
            container.execute(['rm', tmp_file])
            self.target.server_id.execute([
                'docker', 'cp',
                tmp_file, self.target.name + ':' + file_destination])
            self.target.server_id.execute(['rm', tmp_file])

#            container.self.execute(['rm', '/home/backup/.ssh/keys/*'],
#                                   username='backup')
            
            if self.target.options['protocol']['value'] == 'ftp':
                self.target.execute([
                    'lftp',
                    'ftp://' + self.target.options['login']['value'] +
                    ':' + self.target.options['password']['value'] + '@' +
                    self.target.options['host']['value'],
                    '-e', '"rm ' + filegz + '; quit"'])
                self.target.execute([
                    'lftp',
                    'ftp://' + self.target.options['login']['value'] +
                    ':' + self.target.options['password']['value'] + '@' +
                    self.target.options['host']['value'],
                    '-e', '"put ' + file_destination + '; quit"'])

        return super(ClouderContainerLink, self).deploy_link()

    @api.multi
    def purge_link(self):
        """
        Remove the backups on the distant container.
        """
        if self.name.type_id.name == 'backup-upload' \
                and self.container_id.application_id.type_id.name == 'backup':
            directory = '/opt/upload/' + self.container_id.name
            self.target.execute(['rm', '-rf', directory])
        return super(ClouderContainerLink, self).purge_link()

