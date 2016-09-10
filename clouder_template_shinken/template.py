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
        return '/usr/local/shinken/etc/hosts/' + self.fulldomain + '.cfg'


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
    def deploy_shinken_server(self, nrpe):
        """
        Deploy the configuration file to watch the server performances.
        """

        server = nrpe.server_id
        self.send(
            modules.get_module_path('clouder_template_shinken') +
            '/res/server-shinken.config', server.shinken_configfile,
            username='shinken')
        self.execute([
            'sed', '-i',
            '"s/IP/' + server.ip + '/g"',
            server.shinken_configfile], username='shinken')
        self.execute([
            'sed', '-i',
            '"s/NAME/' + server.name + '/g"',
            server.shinken_configfile], username='shinken')
        self.execute([
            'sed', '-i',
            '"s/SSHPORT/' + str(server.ssh_port) + '/g"',
            server.shinken_configfile], username='shinken')
        self.execute([
            'sed', '-i',
            '"s/NRPEPORT/' + nrpe.ports['nrpe']['hostport'] + '/g"',
            server.shinken_configfile], username='shinken')
        self.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                     username='shinken')

    @api.multi
    def purge_shinken_server(self, nrpe):
        """
        Remove the configuration file.
        """
        self.execute(['rm', nrpe.server_id.shinken_configfile],
                     username='shinken')
        self.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                     username='shinken')

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
                '/usr/local/shinken/etc/services/clouder.cfg',
                username='shinken')
            self.execute([
                'sed', '-i', '"s/SYSADMIN_MAIL/' +
                self.email_sysadmin + '/g"',
                '/usr/local/shinken/etc/services/clouder.cfg'],
                username='shinken')
            self.execute(
                ['rm', '/usr/local/shinken/etc/hosts/localhost.cfg'],
                username='shinken')


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

    @api.multi
    def deploy_post(self):
        """
        Update odoo configuration.
        """
        res = super(ClouderBase, self).deploy_post()
        if self.application_id.type_id.name == 'shinken':
            self.container_id.execute([
                'sed', '-i', '"s/SHINKENDOMAIN/' +
                self.fulldomain + '/g"',
                '/usr/local/shinken/etc/services/clouder.cfg'],
                username='shinken')

            self.container_id.execute(
                ['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                username='shinken')
        return res

    @api.multi
    def purge_post(self):
        """
        Remove filestore.
        """
        res = super(ClouderBase, self).purge_post()
        if self.application_id.type_id.name == 'shinken':
            self.container_id.execute([
                'sed', '-i', '"s/' + self.fulldomain + '/SHINKENDOMAIN/g"',
                '/usr/local/shinken/etc/services/clouder.cfg'],
                username='shinken')
            self.container_id.execute(
                ['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                username='shinken')
        return res


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
        if self.name.type_id.name == 'shinken':
            config_file = 'container-shinken'
            if not self.container_id.autosave:
                config_file = 'container-shinken-nosave'
            self.target.send(
                modules.get_module_path('clouder_template_shinken') +
                '/res/' + config_file + '.config',
                self.container_id.shinken_configfile, username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/BACKUPIP/' +
                self.container_id.backup_ids[0].server_id.ip + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/PORT/' +
                self.container_id.backup_ids[0].ports['nrpe']['hostport']
                + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i', '"s/METHOD/' +
                self.container_id.backup_ids[0].backup_method + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i', '"s/TYPE/container/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/BACKUPIP/' +
                self.container_id.backup_ids[0].server_id.ip + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/UNIQUE_NAME/' + self.container_id.fullname + '/g"',
                self.container_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/HOST/' + self.container_id.server_id.name + '/g"',
                self.container_id.shinken_configfile], username='shinken')

            self.target.execute(
                ['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                username='shinken')

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderContainerLink, self).purge_link()
        if self.name.type_id.name == 'shinken':
            self.target.execute(['rm', self.container_id.shinken_configfile],
                                username='shinken')
            self.target.execute(
                ['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                username='shinken')


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
        if self.name.type_id.name == 'shinken':
            config_file = 'base-shinken'
            if not self.base_id.autosave:
                config_file = 'base-shinken-nosave'
            self.target.send(
                modules.get_module_path('clouder_template_shinken') +
                '/res/' + config_file + '.config',
                self.base_id.shinken_configfile, username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/BACKUPIP/' +
                self.base_id.backup_ids[0].server_id.ip + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/PORT/' +
                self.base_id.backup_ids[0].ports['nrpe']['hostport'] + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i', '"s/METHOD/' +
                self.base_id.backup_ids[0].backup_method + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i', '"s/TYPE/base/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/UNIQUE_NAME/' + self.base_id.fullname + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/DATABASES/' + self.base_id.databases_comma + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i', '"s/BASE/' + self.base_id.name + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/DOMAIN/' + self.base_id.fulldomain + '/g"',
                self.base_id.shinken_configfile], username='shinken')
            self.target.execute(
                ['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                username='shinken')

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderBaseLink, self).purge_link()
        if self.name.type_id.name == 'shinken':
            self.target.execute(['rm', self.base_id.shinken_configfile],
                                username='shinken')
            self.target.execute(
                ['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                username='shinken')
