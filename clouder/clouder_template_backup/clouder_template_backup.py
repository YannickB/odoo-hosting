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
from openerp.exceptions import except_orm


import logging

_logger = logging.getLogger(__name__)


class ClouderContainerLink(models.Model):
    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):

        if self.target.application_id.code == 'backup-upl' \
                and self.application_id.type_id.name == 'backup':
            directory = '/opt/upload/' + self.container_id.fullname
            ssh_link, sftp_link = self.connect(self.target.fullname)
            self.execute(ssh_link, ['mkdir', '-p', directory])
            ssh_link.close(), sftp_link.close()

            ssh = self.connect(self.container_id.fullname,
                                     username='backup')
            self.send(ssh, self.home_directory + '/.ssh/config',
                      '/home/backup/.ssh/config')
            self.send(ssh, self.home_directory + '/.ssh/keys/' +
                      self.target.fullname + '.pub',
                      '/home/backup/.ssh/keys/' +
                      self.target.fullname + '.pub')
            self.send(ssh, self.home_directory + '/.ssh/keys/' +
                      self.target.fullname,
                      '/home/backup/.ssh/keys/' + self.target.fullname)
            self.execute(ssh, ['chmod', '-R', '700', '/home/backup/.ssh'])
            self.execute(ssh, ['rsync', '-ra', '/opt/backup/',
                               self.target.fullname + ':' + directory])
            self.execute(ssh, ['rm', '/home/backup/.ssh/keys/*'])
            ssh.close()

        return super(ClouderContainerLink, self).deploy_link()

    @api.multi
    def purge_link(self):
        if self.target.application_id.code == 'backup-upl' \
                and self.application_id.type_id.name == 'backup':
            directory = '/opt/upload/' + self.container_id.fullname
            ssh = self.connect(self.target.fullname)
            self.execute(ssh, ['rm', '-rf', directory])
            ssh.close()
        return super(ClouderContainerLink, self).purge_link()

