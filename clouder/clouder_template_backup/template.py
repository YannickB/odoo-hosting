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
        #TODO
        # if self.name.name.code == 'backup-upl' \
        #         and self.container_id.application_id.type_id.name == 'backup':
        #     directory = '/opt/upload/' + self.container_id.fullname
        #     self.target.execute(['mkdir', '-p', directory])
        #
        #     container = self.container_id
        #     container.send(self.home_directory + '/.ssh/config',
        #               '/home/backup/.ssh/config', username='backup')
        #     container.send(self.home_directory + '/.ssh/keys/' +
        #               self.target.fullname + '.pub',
        #               '/home/backup/.ssh/keys/' +
        #               self.target.fullname + '.pub', username='backup')
        #     container.send(self.home_directory + '/.ssh/keys/' +
        #               self.target.fullname,
        #               '/home/backup/.ssh/keys/' + self.target.fullname, username='backup')
        #     container.execute(['chmod', '-R', '700', '/home/backup/.ssh'], username='backup')
        #     container.execute([
        #         'rsync', "-e 'ssh -o StrictHostKeyChecking=no'", '-ra',
        #         '/opt/backup/', self.target.fullname + ':' + directory], username='backup')
        #     container.self.execute(['rm', '/home/backup/.ssh/keys/*'], username='backup')

        return super(ClouderContainerLink, self).deploy_link()

    @api.multi
    def purge_link(self):
        """
        Remove the backups on the distant container.
        """
        if self.name.name.code == 'backup-upl' \
                and self.container_id.application_id.type_id.name == 'backup':
            directory = '/opt/upload/' + self.container_id.fullname
            self.target.execute(['rm', '-rf', directory])
        return super(ClouderContainerLink, self).purge_link()

