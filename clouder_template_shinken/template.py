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

try:
    from odoo import models, api, modules
except ImportError:
    from openerp import models, api, modules


class ClouderNode(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.node'

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

    _inherit = 'clouder.service'

    @property
    def shinken_configfile(self):
        """
        Property returning the shinken config file.
        """
        return '/usr/local/shinken/etc/services/' + self.fullname + '.cfg'

    @api.multi
    def deploy_shinken_node(self, nrpe):
        """
        Deploy the configuration file to watch the node performances.
        """

        node = nrpe.node_id
        self.send(
            modules.get_module_path('clouder_template_shinken') +
            '/res/node-shinken.config', node.shinken_configfile,
            username='shinken')
        self.execute([
            'sed', '-i',
            '"s/IP/' + node.ip + '/g"',
            node.shinken_configfile], username='shinken')
        self.execute([
            'sed', '-i',
            '"s/NAME/' + node.name + '/g"',
            node.shinken_configfile], username='shinken')
        self.execute([
            'sed', '-i',
            '"s/SSHPORT/' + str(node.ssh_port) + '/g"',
            node.shinken_configfile], username='shinken')
        self.execute([
            'sed', '-i',
            '"s/NRPEPORT/' + nrpe.ports['nrpe']['hostport'] + '/g"',
            node.shinken_configfile], username='shinken')
        self.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                     username='shinken')

    @api.multi
    def purge_shinken_node(self, nrpe):
        """
        Remove the configuration file.
        """
        self.execute(['rm', nrpe.node_id.shinken_configfile],
                     username='shinken')
        self.execute(['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                     username='shinken')

    @api.multi
    def deploy_post(self):
        """
        Add the general configuration files.
        """
        super(ClouderContainer, self).deploy_post()
        if self.application_id.type_id.name == 'shinken' \
                and self.application_id.check_tags(['data']):
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
            self.service_id.execute([
                'sed', '-i', '"s/SHINKENDOMAIN/' +
                self.fulldomain + '/g"',
                '/usr/local/shinken/etc/services/clouder.cfg'],
                username='shinken')

            self.service_id.execute(
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
            self.service_id.execute([
                'sed', '-i', '"s/' + self.fulldomain + '/SHINKENDOMAIN/g"',
                '/usr/local/shinken/etc/services/clouder.cfg'],
                username='shinken')
            self.service_id.execute(
                ['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                username='shinken')
        return res


class ClouderContainerLink(models.Model):
    """
    Add methods to manage the shinken specificities.
    """

    _inherit = 'clouder.service.link'

    @api.multi
    def deploy_link(self):
        """
        Deploy the configuration file to watch the service.
        """
        super(ClouderContainerLink, self).deploy_link()
        if self.target \
                and self.target.application_id.type_id.name == 'shinken':
            if self.service_id.auto_backup:
                config_file = 'service-shinken'
                self.target.send(
                    modules.get_module_path('clouder_template_shinken') +
                    '/res/' + config_file + '.config',
                    self.service_id.shinken_configfile, username='shinken')
                self.target.execute([
                    'sed', '-i',
                    '"s/BACKUPIP/' +
                    self.service_id.backup_ids[0].node_id.ip + '/g"',
                    self.service_id.shinken_configfile], username='shinken')
                self.target.execute([
                    'sed', '-i',
                    '"s/PORT/' +
                    self.service_id.backup_ids[0].ports['nrpe']['hostport'] +
                    '/g"',
                    self.service_id.shinken_configfile], username='shinken')
                self.target.execute([
                    'sed', '-i', '"s/METHOD/' +
                    self.service_id.backup_ids[0].backup_method + '/g"',
                    self.service_id.shinken_configfile], username='shinken')
                self.target.execute([
                    'sed', '-i', '"s/TYPE/service/g"',
                    self.service_id.shinken_configfile], username='shinken')
                self.target.execute([
                    'sed', '-i',
                    '"s/BACKUPIP/' +
                    self.service_id.backup_ids[0].node_id.ip + '/g"',
                    self.service_id.shinken_configfile], username='shinken')
                self.target.execute([
                    'sed', '-i',
                    '"s/UNIQUE_NAME/' + self.service_id.fullname + '/g"',
                    self.service_id.shinken_configfile], username='shinken')
                self.target.execute([
                    'sed', '-i',
                    '"s/HOST/' + self.service_id.node_id.name + '/g"',
                    self.service_id.shinken_configfile], username='shinken')

                self.target.execute(
                    ['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                    username='shinken')

    @api.multi
    def purge_link(self):
        """
        Remove the configuration file.
        """
        super(ClouderContainerLink, self).purge_link()
        if self.target \
                and self.target.application_id.type_id.name == 'shinken':
            self.target.execute(['rm', self.service_id.shinken_configfile],
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
        if self.target \
                and self.target.application_id.type_id.name == 'shinken':
            config_file = 'base-shinken'
            if not self.base_id.auto_backup:
                config_file = 'base-shinken-no-backup'
            self.target.send(
                modules.get_module_path('clouder_template_shinken') +
                '/res/' + config_file + '.config',
                self.base_id.shinken_configfile, username='shinken')
            self.target.execute([
                'sed', '-i',
                '"s/BACKUPIP/' +
                self.base_id.backup_ids[0].node_id.ip + '/g"',
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
                '"s/DATABASES/' + self.base_id.db_names_comma + '/g"',
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
        if self.target \
                and self.target.application_id.type_id.name == 'shinken':
            self.target.execute(['rm', self.base_id.shinken_configfile],
                                username='shinken')
            self.target.execute(
                ['/usr/local/shinken/bin/init.d/shinken', 'reload'],
                username='shinken')
