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
            ssh = self.connect(self.supervision_id.fullname,
                               username='shinken')
            self.send(ssh,
                      modules.get_module_path('clouder_template_shinken') +
                      '/res/server-shinken.config', self.shinken_configfile)
            self.execute(ssh, ['sed', '-i',
                               '"s/NAME/' + self.name + '/g"',
                               self.shinken_configfile])
            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])
            ssh.close()

    @api.multi
    def purge(self):
        """
        Remove the configuration file.
        """
        if self.supervision_id:
            ssh = self.connect(self.supervision_id.fullname,
                               username='shinken')
            self.execute(ssh, ['rm', self.shinken_configfile])
            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])
            ssh.close()


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
            ssh = self.connect(self.fullname,
                               username='shinken')
            self.send(ssh,
                      modules.get_module_path('clouder_template_shinken') +
                      '/res/general-shinken.config',
                      '/usr/local/shinken/etc/services/clouder.cfg')
            self.execute(ssh, [
                'sed', '-i', '"s/SYSADMIN_MAIL/' +
                self.email_sysadmin + '/g"',
                '/usr/local/shinken/etc/services/clouder.cfg'])
            self.send(ssh,
                      modules.get_module_path('clouder_template_shinken') +
                      '/res/control_backup.sh',
                      '/home/shinken/control_backup.sh')
            self.execute(ssh, ['chmod', '+x',
                               '/home/shinken/control_backup.sh'])
            self.execute(ssh, ['rm',
                               '/usr/local/shinken/etc/hosts/localhost.cfg'])
            ssh.close()

    @api.multi
    def deploy_key(self):
        """
        Reset the backup ssh key in shinken containers after we change the
        key of a backup container
        """
        super(ClouderContainer, self).deploy_key()
        if self.application_id.type_id.name == 'backup':
            shinkens = {}
            containers = self.search([('backup_ids', 'in', self.id)])
            for container in containers:
                shinken_links = self.env['clouder.container.link'].search([
                    ('container_id', '=', container.id),
                    ('name.name.code', '=', 'shinken'),
                    ('target', '!=', False)
                ])
                for shinken_link in shinken_links:
                    shinkens[shinken_link.target.id] = {
                        'shinken': shinken_link.target,
                        'container': container
                    }

            for key, shinken in shinkens.iteritems():
                ssh = self.connect(shinken['shinken'].fullname,
                                   username='shinken')
                send_key_to_shinken(ssh, shinken['container'])
                ssh.close()


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


def send_key_to_shinken(ssh, self):
    """
    Update the ssh key in the shinken container so it can access the
    backup container.

    :param ssh: The connection to the shinken container.
    """
    for backup in self.backup_ids:
        self.execute(ssh, ['rm', '-rf', '/home/shinken/.ssh/keys/' +
                           backup.fullname + '*'])
        self.send(
            ssh, self.home_directory + '/.ssh/keys/' +
            backup.fullname + '.pub', '/home/shinken/.ssh/keys/' +
            backup.fullname + '.pub')
        self.send(ssh, self.home_directory + '/.ssh/keys/' +
                  backup.fullname, '/home/shinken/.ssh/keys/' +
                  backup.fullname)
        self.execute(ssh, ['chmod', '-R', '700', '/home/shinken/.ssh'])
        self.execute(ssh, [
            'sed', '-i', "'/Host " + backup.fullname +
            "/,/END " + backup.fullname + "/d'",
            '/home/shinken/.ssh/config'])
        self.execute(ssh, [
            'echo "Host ' + backup.fullname +
            '" >> /home/shinken/.ssh/config'])
        self.execute(ssh, [
            'echo "    Hostname ' +
            backup.server_id.name + '" >> /home/shinken/.ssh/config'])
        self.execute(ssh, [
            'echo "    Port ' + str(backup.ssh_port) +
            '" >> /home/shinken/.ssh/config'])
        self.execute(ssh, [
            'echo "    User backup" >> /home/shinken/.ssh/config'])
        self.execute(ssh, [
            'echo "    IdentityFile  ~/.ssh/keys/' +
            backup.fullname + '" >> /home/shinken/.ssh/config'])
        self.execute(ssh, ['echo "#END ' + backup.fullname +
                           '" >> ~/.ssh/config'])


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
            ssh = self.connect(self.target.fullname,
                               username='shinken')
            config_file = 'container-shinken'
            if self.container_id.nosave:
                config_file = 'container-shinken-nosave'
            self.send(ssh,
                      modules.get_module_path('clouder_template_shinken') +
                      '/res/' + config_file + '.config',
                      self.container_id.shinken_configfile)
            self.execute(ssh, [
                'sed', '-i', '"s/METHOD/' +
                self.container_id.backup_ids[0].backup_method + '/g"',
                self.container_id.shinken_configfile])
            self.execute(ssh, ['sed', '-i', '"s/TYPE/container/g"',
                               self.container_id.shinken_configfile])
            self.execute(ssh, [
                'sed', '-i',
                '"s/CONTAINER/' + self.container_id.backup_ids[0]
                         .fullname + '/g"',
                self.container_id.shinken_configfile])
            self.execute(ssh, [
                'sed', '-i',
                '"s/UNIQUE_NAME/' + self.container_id.fullname + '/g"',
                self.container_id.shinken_configfile])
            self.execute(ssh, [
                'sed', '-i',
                '"s/HOST/' + self.container_id.server_id.name + '/g"',
                self.container_id.shinken_configfile])
            self.execute(ssh, [
                'sed', '-i',
                '"s/PORT/' + str(self.container_id.ssh_port) + '/g"',
                self.container_id.shinken_configfile])

            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])

            send_key_to_shinken(ssh, self.container_id)

            ssh.close()

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderContainerLink, self).purge_link()
        if self.name.name.code == 'shinken':
            ssh = self.connect(self.target.fullname,
                               username='shinken')
            self.execute(ssh, ['rm', self.container_id.shinken_configfile])
            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])
            ssh.close()


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
            ssh = self.connect(self.target.fullname,
                               username='shinken')
            config_file = 'base-shinken'
            if self.base_id.nosave:
                config_file = 'base-shinken-nosave'
            self.send(ssh,
                      modules.get_module_path('clouder_template_shinken') +
                      '/res/' + config_file + '.config',
                      self.base_id.shinken_configfile)
            self.execute(ssh, ['sed', '-i', '"s/TYPE/base/g"',
                               self.base_id.shinken_configfile])
            self.execute(ssh, [
                'sed', '-i',
                '"s/UNIQUE_NAME/' + self.base_id.fullname_ + '/g"',
                self.base_id.shinken_configfile])
            self.execute(ssh, [
                'sed', '-i',
                '"s/DATABASES/' + self.base_id.databases_comma + '/g"',
                self.base_id.shinken_configfile])
            self.execute(ssh,
                         ['sed', '-i', '"s/BASE/' + self.base_id.name + '/g"',
                          self.base_id.shinken_configfile])
            self.execute(ssh, [
                'sed', '-i',
                '"s/DOMAIN/' + self.base_id.domain_id.name + '/g"',
                self.base_id.shinken_configfile])
            self.execute(ssh, [
                'sed', '-i', '"s/METHOD/' +
                self.base_id.backup_ids[0].backup_method + '/g"',
                self.base_id.shinken_configfile])
            self.execute(ssh, [
                'sed', '-i',
                '"s/CONTAINER/' + self.base_id
                         .backup_ids[0].fullname + '/g"',
                self.base_id.shinken_configfile])
            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])

            send_key_to_shinken(ssh, self.base_id)

            ssh.close()

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderBaseLink, self).purge_link()
        if self.name.name.code == 'shinken':
            ssh = self.connect(self.target.fullname,
                               username='shinken')
            self.execute(ssh, ['rm', self.base_id.shinken_configfile])
            self.execute(ssh, ['/etc/init.d/shinken', 'reload'])
            ssh.close()