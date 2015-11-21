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


class ClouderServer(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.server'

    @property
    def shinken_configfile(self):
        """
        Property returning the shinken config file.
        """
        return '/usr/local/shinken/etc/hosts/' + self.name + '.cfg'

    @api.multi
    def deploy(self):
        """
        Deploy the configuration file to watch the server performances.
        """
        super(ClouderServer, self).deploy()

        if self.supervision_id:
            self.supervision_id.send(
                      modules.get_module_path('clouder_template_shinken') +
                      '/res/server-shinken.config', self.shinken_configfile, username='shinken')
            self.supervision_id.execute(['sed', '-i',
                               '"s/NAME/' + self.name + '/g"',
                               self.shinken_configfile], username='shinken')
            self.supervision_id.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'], username='shinken')

    @api.multi
    def purge(self):
        """
        Remove the configuration file.
        """
        if self.supervision_id:
            self.supervision_id.execute(['rm', self.shinken_configfile], username='shinken')
            self.supervision_id.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'], username='shinken')

        super(ClouderServer, self).purge()


class ClouderContainer(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.container'

    @property
    def shinken_configfile(self):
        """
        Property returning the shinken config file.
        """
        return '/usr/local/shinken/etc/services/' + self.fullname + '.cfg'

    @api.multi
    def deploy_post(self):
        """
        Add the general configuration files.
        """
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'shinken':
            self.send(
                      modules.get_module_path('clouder_template_shinken') +
                      '/res/general-shinken.config',
                      '/usr/local/shinken/etc/services/clouder.cfg', username='shinken')
            self.execute([
                'sed', '-i', '"s/SYSADMIN_MAIL/' +
                self.email_sysadmin + '/g"',
                '/usr/local/shinken/etc/services/clouder.cfg'], username='shinken')
            self.execute(['rm',
                               '/usr/local/shinken/etc/hosts/localhost.cfg'], username='shinken')


class ClouderBase(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.base'

    @property
    def shinken_configfile(self):
        """
        Property returning the shinken config file.
        """
        return '/usr/local/shinken/etc/services/' + self.fullname + '.cfg'


def send_key_to_shinken(shinken, self):
    """
    Update the ssh key in the shinken container so it can access the
    backup container.

    :param ssh: The connection to the shinken container.
    """
    for backup in self.backup_ids:
        shinken.execute(['rm', '-rf', '/home/shinken/.ssh/keys/' +
                           backup.server_id.name + '*'], username='shinken')
        shinken.send(
            self.home_directory + '/.ssh/keys/' +
            backup.server_id.name + '.pub', '/home/shinken/.ssh/keys/' +
            backup.server_id.name + '.pub', username='shinken')
        shinken.send(self.home_directory + '/.ssh/keys/' +
                  backup.server_id.name, '/home/shinken/.ssh/keys/' +
                  backup.server_id.name, username='shinken')
        shinken.execute(['chmod', '-R', '700', '/home/shinken/.ssh'], username='shinken')
        shinken.execute([
            'sed', '-i', "'/Host " + backup.server_id.name +
            "/,/END " + backup.server_id.name + "/d'",
            '/home/shinken/.ssh/config'], username='shinken')
        shinken.execute([
            'echo "Host ' + backup.server_id.name +
            '" >> /home/shinken/.ssh/config'], username='shinken')
        shinken.execute([
            'echo "    Hostname ' +
            backup.server_id.ip + '" >> /home/shinken/.ssh/config'], username='shinken')
        shinken.execute([
            'echo "    Port ' + str(backup.server_id.ssh_port) +
            '" >> /home/shinken/.ssh/config'], username='shinken')
        shinken.execute([
            'echo "    User backup" >> /home/shinken/.ssh/config'], username='shinken')
        shinken.execute([
            'echo "    IdentityFile  ~/.ssh/keys/' +
            backup.server_id.name + '" >> /home/shinken/.ssh/config'], username='shinken')
        shinken.execute(['echo "#END ' + backup.server_id.name +
                           '" >> ~/.ssh/config'], username='shinken')


class ClouderContainerLink(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.container.link'

    @api.multi
    def deploy_link(self):
        """
        Deploy the configuration file to watch the container.
        """
        super(ClouderContainerLink, self).deploy_link()
        if self.name.name.code == 'shinken':
            config_file = 'container-shinken'
            if not self.container_id.save:
                config_file = 'container-shinken-nosave'
            self.target.send(
                      modules.get_module_path('clouder_template_shinken') +
                      '/res/' + config_file + '.config',
                      self.container_id.shinken_configfile, username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/BACKUPIP/' + self.container_id.backup_ids[0].server_id.ip + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/PORT/' + self.container_id.backup_ids[0].ports['nrpe']['hostport'] + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i', '"s/METHOD/' +
                self.container_id.backup_ids[0].backup_method + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute(['sed', '-i', '"s/TYPE/container/g"',
                               self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/BACKUPIP/' + self.container_id.backup_ids[0].server_id.ip + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/UNIQUE_NAME/' + self.container_id.fullname + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/HOST/' + self.container_id.server_id.name + '/g"',
                self.container_id.shinken_configfile], username='shinken')

            self.target.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'], username='shinken')

            send_key_to_shinken(self.target, self.container_id)

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderContainerLink, self).purge_link()
        if self.name.name.code == 'shinken':
            self.target.execute(['rm', self.container_id.shinken_configfile], username='shinken')
            self.target.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'], username='shinken')


class ClouderBaseLink(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_link(self):
        """
        Deploy the configuration file to watch the base.
        """
        super(ClouderBaseLink, self).deploy_link()
        if self.name.name.code == 'shinken':
            config_file = 'base-shinken'
            if self.base_id.nosave:
                config_file = 'base-shinken-nosave'
            self.target.send(
                      modules.get_module_path('clouder_template_shinken') +
                      '/res/' + config_file + '.config',
                      self.base_id.shinken_configfile, username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/BACKUPIP/' + self.base_id.backup_ids[0].server_id.ip + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/PORT/' + self.base_id.backup_ids[0].ports['nrpe']['hostport'] + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i', '"s/METHOD/' +
                self.base_id.backup_ids[0].backup_method + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute(['sed', '-i', '"s/TYPE/base/g"',
                               self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/UNIQUE_NAME/' + self.base_id.fullname + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/DATABASES/' + self.base_id.databases_comma + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute(
                         ['sed', '-i', '"s/BASE/' + self.base_id.name + '/g"',
                          self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/DOMAIN/' + self.base_id.domain_id.name + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'], username='shinken')

            send_key_to_shinken(self.target, self.base_id)

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderBaseLink, self).purge_link()
        if self.name.name.code == 'shinken':
            self.target.execute(['rm', self.base_id.shinken_configfile], username='shinken')
            self.target.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'], username='shinken')