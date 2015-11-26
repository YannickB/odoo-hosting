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


class ClouderBase(models.Model):
    """
    Add methods to manage the proxy specificities.
    """

    _inherit = 'clouder.base'

    @property
    def nginx_configfile(self):
        """
        Property returning the nginx config file.
        """
        return '/etc/nginx/sites-available/' + self.fullname


class ClouderBaseLink(models.Model):
    """
    Add methods to manage the proxy specificities.
    """

    _inherit = 'clouder.base.link'

    @api.multi
    def deploy_link(self):
        """
        Configure the proxy to redirect to the application port.
        """
        super(ClouderBaseLink, self).deploy_link()
        if self.name.name.code == 'proxy':
            if not self.base_id.ssl_only:
                configfile = 'proxy.config'
            else:
                configfile = 'proxy-sslonly.config'
            target = self.target
            target.send(
                modules.get_module_path(
                    'clouder_template_' +
                    self.base_id.application_id.type_id.name
                ) + '/res/' + configfile, self.base_id.nginx_configfile)
            target.execute([
                'sed', '-i', '"s/BASE/' + self.base_id.name + '/g"',
                self.base_id.nginx_configfile])
            target.execute([
                'sed', '-i', '"s/DOMAIN/' + self.base_id.domain_id.name +
                '/g"', self.base_id.nginx_configfile])
            target.execute([
                'sed', '-i', '"s/SERVER/' +
                self.base_id.container_id.server_id.name + '/g"',
                self.base_id.nginx_configfile])
            if 'http' in self.base_id.container_id.ports:
                target.execute([
                    'sed', '-i', '"s/PORT/' +
                    self.base_id.container_ids.ports['http']['hostport'] +
                    '/g"', self.base_id.nginx_configfile])
            # self.deploy_prepare_apache(cr, uid, vals, context)
            cert_file = '/etc/ssl/certs/' + self.base_id.name + '.' + \
                        self.base_id.domain_id.name + '.crt'
            key_file = '/etc/ssl/private/' + self.base_id.name + '.' +\
                       self.base_id.domain_id.name + '.key'
            if self.base_id.cert_cert and self.base_id.cert_key:
                target.execute([
                    'echo', '"' + self.base_id.cert_cert + '"', '>', cert_file
                ])
                target.execute([
                    'echo', '"' + self.base_id.cert_key + '"', '>', key_file])
            elif self.base_id.domain_id.cert_cert\
                    and self.base_id.domain_id.cert_key:
                target.execute([
                    'echo', '"' + self.base_id.domain_id.cert_cert + '"',
                    '>', cert_file])
                target.execute([
                    'echo', '"' + self.base_id.domain_id.domain_cert_key + '"',
                    '>', key_file])
            else:
                target.execute([
                    'openssl', 'req', '-x509', '-nodes', '-days', '365',
                    '-newkey', 'rsa:2048', '-out', cert_file,
                    ' -keyout', key_file, '-subj', '"/C=FR/L=Paris/O=' +
                    self.base_id.domain_id.organisation +
                    '/CN=' + self.base_id.name +
                    '.' + self.base_id.domain_id.name + '"'])
            target.execute([
                'ln', '-s', self.base_id.nginx_configfile,
                '/etc/nginx/sites-enabled/' + self.base_id.fullname])
            target.execute(['/etc/init.d/nginx', 'reload'])

    @api.multi
    def purge_link(self):
        """
        Remove the redirection.
        """
        super(ClouderBaseLink, self).purge_link()
        if self.name.name.code == 'proxy':
            target = self.target
            target.execute([
                'rm',
                '/etc/nginx/sites-enabled/' + self.base_id.fullname])
            target.execute(['rm', self.base_id.nginx_configfile])
            target.execute([
                'rm', '/etc/ssl/certs/' + self.base_id.name +
                '.' + self.base_id.domain_id.name + '.*'])
            target.execute([
                'rm', '/etc/ssl/private/' + self.base_id.name +
                '.' + self.base_id.domain_id.name + '.*'])
            target.execute(['/etc/init.d/nginx', 'reload'])