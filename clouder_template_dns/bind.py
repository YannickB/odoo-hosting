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

from datetime import datetime

import socket


class ClouderDomain(models.Model):
    """
    Add method to manage domain general configuration on the bind service.
    """

    _inherit = 'clouder.domain'

    @property
    def configfile(self):
        """
        Property returning the path to the domain config file
        in the bind service.
        """
        return'/etc/bind/db.' + self.name

    @api.multi
    def refresh_serial(self, domain=False):
        """
        Refresh the serial number in the config file
        """
        if self.dns_id and self.dns_id.application_id.type_id.name == 'bind':
            self.dns_id.execute([
                'sed', '-i',
                '"s/[0-9]* ;serial/' +
                datetime.now().strftime('%m%d%H%M%S') + ' ;serial/g"',
                self.configfile])
            self.dns_id.start()

            if domain:
                try:
                    socket.gethostbyname(domain)
                except:
                    self.dns_id.start()
                    pass

    @api.multi
    def deploy(self):
        """
        Configure the domain in the bind service, if configured.
        """

        super(ClouderDomain, self).deploy()

        if self.dns_id and self.dns_id.application_id.type_id.name == 'bind':
            self.dns_id.send(
                modules.get_module_path('clouder_template_dns') +
                '/res/bind.config', self.configfile)
            self.dns_id.execute([
                'sed', '-i', '"s/DOMAIN/' + self.name + '/g"',
                self.configfile])
            self.dns_id.execute([
                'sed', '-i',
                '"s/IP/' + self.dns_id.node_id.public_ip + '/g"',
                self.configfile])
            self.dns_id.execute([
                "echo 'zone \"" + self.name + "\" {' >> /etc/bind/named.conf"])
            self.dns_id.execute([
                'echo "type master;" >> /etc/bind/named.conf'])

            self.dns_id.execute([
                "echo 'file \"/etc/bind/db." +
                self.name + "\";' >> /etc/bind/named.conf"])
            self.dns_id.execute(['echo "notify yes;" >> /etc/bind/named.conf'])
            self.dns_id.execute(['echo "};" >> /etc/bind/named.conf'])
            self.dns_id.execute([
                'echo "//END ' + self.name + '" >> /etc/bind/named.conf'])
            self.refresh_serial()

    @api.multi
    def purge(self):
        """
        Remove the domain config in the bind service.
        """
        if self.dns_id and self.dns_id.application_id.type_id.name == 'bind':
            self.dns_id.execute([
                'sed', '-i',
                r"'/zone\s\"" + self.name + r"\"/,/END\s" + self.name + "/d'",
                '/etc/bind/named.conf'])
            self.dns_id.execute(['rm', self.configfile])
            self.dns_id.execute(['/etc/init.d/bind9 reload'])


class ClouderBaseLink(models.Model):
    """
    Add method to manage links between bases and the bind service.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_dns_config(self, name, type, value):
        super(ClouderBaseLink, self).deploy_dns_config(name, type, value)

        if self.name.type_id.name == 'bind':

            if type == 'MX':
                type = 'MX 1'

            self.target.execute([
                'echo "%s IN %s %s ; %s:%s\" >> %s' %
                (name, type, value, type, self.base_id.fulldomain,
                 self.base_id.domain_id.configfile)])
            self.base_id.domain_id.refresh_serial(self.base_id.fulldomain)

    @api.multi
    def purge_dns_config(self, name, type):

        super(ClouderBaseLink, self).purge_dns_config(name, type)

        if self.name.type_id.name == 'bind':
            self.target.execute([
                'sed', '-i',
                '"/%s:%s/d"' % (type, self.base_id.fulldomain),
                self.base_id.domain_id.configfile])
            self.base_id.domain_id.refresh_serial()
