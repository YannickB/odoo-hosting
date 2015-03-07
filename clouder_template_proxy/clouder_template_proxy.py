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

from openerp import modules
from openerp import models, fields, api, _


class ClouderBase(models.Model):
    _inherit = 'clouder.base'

    @property
    def nginx_configfile(self):
        return '/etc/nginx/sites-available/' + self.fullname


class ClouderBaseLink(models.Model):
    _inherit = 'clouder.base.link'


    @api.multi
    def deploy_link(self):
        super(ClouderBaseLink, self).deploy_link()
        if self.name.name.code == 'proxy':
            if not self.base_id.ssl_only:
                file = 'proxy.config'
            else:
                file = 'proxy-sslonly.config'
            ssh = self.connect(self.target.fullname)
            self.send(ssh,
                      modules.get_module_path(
                          'clouder_template_' +
                          self.base_id.application_id.type_id.name
                      ) + '/res/' + file, self.base_id.nginx_configfile)
            self.execute(ssh,
                         ['sed', '-i', '"s/BASE/' + self.base_id.name + '/g"',
                          self.base_id.nginx_configfile])
            self.execute(ssh, [
                'sed', '-i', '"s/DOMAIN/' + self.base_id.domain_id.name +
                '/g"', self.base_id.nginx_configfile])
            self.execute(ssh, [
                'sed', '-i', '"s/SERVER/' +
                self.base_id.service_id.container_id.server_id.name + '/g"',
                self.base_id.nginx_configfile])
            if 'port' in self.base_id.service_id.options:
                self.execute(ssh, [
                    'sed', '-i', '"s/PORT/' +
                    self.base_id.service_id.port['hostport'] +
                    '/g"', self.base_id.nginx_configfile])
            # self.deploy_prepare_apache(cr, uid, vals, context)
            cert_file = '/etc/ssl/certs/' + self.base_id.name + '.' + \
                        self.base_id.domain_id.name + '.crt'
            key_file = '/etc/ssl/private/' + self.base_id.name + '.' +\
                       self.base_id.domain_id.name + '.key'
            if self.base_id.cert_cert and self.base_id.cert_key:
                self.execute(ssh,[
                    'echo', '"' + self.base_id.cert_cert + '"', '>', cert_file])
                self.execute(ssh, [
                    'echo', '"' + self.base_id.cert_key + '"', '>', key_file])
            elif self.base_id.domain_id.cert_cert\
                    and self.base_id.domain_id.cert_key:
                self.execute(ssh, [
                    'echo', '"' + self.base_id.domain_id.cert_cert + '"',
                    '>', cert_file])
                self.execute(ssh, [
                    'echo', '"' + self.base_id.domain_id.domain_cert_key + '"',
                    '>', key_file])
            else:
                self.execute(ssh, [
                    'openssl', 'req', '-x509', '-nodes', '-days', '365',
                    '-newkey', 'rsa:2048', '-out', cert_file,
                    ' -keyout', key_file, '-subj', '"/C=FR/L=Paris/O=' +
                    self.base_id.domain_id.organisation +
                    '/CN=' + self.base_id.name +
                    '.' + self.base_id.domain_id.name + '"'])
            self.execute(ssh, [
                'ln', '-s', self.base_id.nginx_configfile,
                '/etc/nginx/sites-enabled/' + self.base_id.fullname])
            self.execute(ssh, ['/etc/init.d/nginx', 'reload'])
            ssh.close()


    @api.multi
    def purge_link(self):
        super(ClouderBaseLink, self).purge_link()
        if self.name.name.code == 'proxy':
            ssh = self.connect(self.target.fullname)
            self.execute(ssh, [
                'rm',
                '/etc/nginx/sites-enabled/' + self.base_id.fullname])
            self.execute(ssh, ['rm', self.base_id.nginx_configfile])
            self.execute(ssh, [
                'rm', '/etc/ssl/certs/' + self.base_id.name +
                '.' + self.base_id.domain_id.name + '.*'])
            self.execute(ssh, [
                'rm', '/etc/ssl/private/' + self.base_id.name +
                '.' + self.base_id.domain_id.name + '.*'])
            self.execute(ssh, ['/etc/init.d/nginx', 'reload'])
            ssh.close()