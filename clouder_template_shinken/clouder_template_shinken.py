# -*- coding: utf-8 -*-
##############################################################################
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

from openerp import modules
from openerp import models, fields, api, _

class ClouderContainer(models.Model):
    _inherit = 'clouder.container'

    shinken_configfile = lambda self : '/usr/local/shinken/etc/services/' + self.fullname() + '.cfg'


class ClouderBase(models.Model):
    _inherit = 'clouder.base'

    shinken_configfile = lambda self : '/usr/local/shinken/etc/services/' + self.unique_name() + '.cfg'


class ClouderContainerLink(models.Model):
    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):
        super(ClouderContainerLink, self).deploy_link()
        if self.name.name.code == 'shinken':
            ssh, sftp = self.connect(self.target.fullname())
            file = 'container-shinken'
            if self.container_id.nosave:
                file = 'container-shinken-nosave'
            sftp.put(modules.get_module_path('clouder_shinken') + '/res/' + file + '.config', self.container_id.shinken_configfile())
            self.execute(ssh, ['sed', '-i', '"s/METHOD/' + self.container_id.backup_ids[0].options()['restore_method']['value'] + '/g"', self.container_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/TYPE/container/g"', self.container_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/CONTAINER/' + self.container_id.backup_ids[0].fullname() + '/g"', self.container_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/UNIQUE_NAME/' + self.container_id.fullname() + '/g"', self.container_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/HOST/' + self.container_id.server_id.name + '/g"', self.container_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/PORT/' + str(self.container_id.ssh_port()) + '/g"', self.container_id.shinken_configfile()])

            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])
            ssh.close(), sftp.close()

    @api.multi
    def purge_link(self):
        super(ClouderContainerLink, self).purge_link()
        if self.name.name.code == 'shinken':
            ssh, sftp = self.connect(self.target.fullname())
            self.execute(ssh, ['rm', self.container_id.shinken_configfile()])
            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])
            ssh.close(), sftp.close()


class ClouderBaseLink(models.Model):
    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_link(self):
        super(ClouderBaseLink, self).deploy_link()
        if self.name.name.code == 'shinken':
            ssh, sftp = self.connect(self.target.fullname())
            file = 'base-shinken'
            if self.base_id.nosave:
                file = 'base-shinken-nosave'
            sftp.put(modules.get_module_path('clouder_shinken') + '/res/' + file + '.config', self.base_id.shinken_configfile())
            self.execute(ssh, ['sed', '-i', '"s/TYPE/base/g"', self.base_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/UNIQUE_NAME/' + self.base_id.unique_name_() + '/g"', self.base_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/DATABASES/' + self.base_id.databases_comma() + '/g"', self.base_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/BASE/' + self.base_id.name + '/g"', self.base_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/DOMAIN/' + self.base_id.domain_id.name + '/g"', self.base_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/METHOD/' + self.base_id.backup_ids[0].options()['restore_method']['value'] + '/g"', self.base_id.shinken_configfile()])
            self.execute(ssh, ['sed', '-i', '"s/CONTAINER/' + self.base_id.backup_ids[0].fullname() + '/g"', self.base_id.shinken_configfile()])
            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])
            ssh.close(), sftp.close()

    @api.multi
    def purge_link(self):
        super(ClouderBaseLink, self).purge_link()
        if self.name.name.code == 'shinken':
            ssh, sftp = self.connect(self.target.fullname())
            self.execute(ssh, ['rm', self.base_id.shinken_configfile()])
            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])
            ssh.close(), sftp.close()