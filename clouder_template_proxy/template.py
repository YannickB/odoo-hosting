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
from datetime import datetime, timedelta


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

    @api.multi
    def generate_cert(self):
        """
        Generate a new certificate
        """
        res = super(ClouderBase, self).generate_cert()
        link_obj = self.env['clouder.base.link']
        proxy_links = link_obj.search([('base_id','=',self.id),('name.name.type_id.name','=','proxy'),('target','!=',False)])
        if proxy_links:
            proxy_link = proxy_links[0]
            proxy = proxy_link.target
            proxy_link.purge_link()
            webroot = '/var/www/' + self.fullname + '-certs'
            proxy.execute(['mkdir -p ' + webroot])
            proxy.send(
                modules.get_module_path(
                    'clouder_template_proxy'
                ) + '/res/nginx.config', self.nginx_configfile)
            proxy.execute([
                'ln', '-s', self.nginx_configfile,
                '/etc/nginx/sites-enabled/' + self.fullname])
            proxy.execute([
                'sed', '-i', '"s/BASE/' + self.name + '/g"',
                self.nginx_configfile])
            domain = self.fulldomain
            if self.is_root:
                domain = domain + ' ' + self.name + '.' + self.fulldomain
            proxy.execute([
                'sed', '-i', '"s/DOMAIN/' + domain +
                '/g"', self.nginx_configfile])
            proxy.execute([
                'sed', '-i', '"s/REPO/' + self.fullname +
                '/g"', self.nginx_configfile])
            proxy.execute(['/etc/init.d/nginx', 'reload'])
            domain = self.fulldomain
            if self.is_root:
                domain = domain + ' -d ' + self.name + '.' + self.fulldomain
            proxy.execute(['/opt/letsencrypt/letsencrypt-auto certonly --webroot -w ' + webroot + ' -d ' + domain])
            key = proxy.execute(['cat', '/etc/letsencrypt/live/' + self.fulldomain + '/privkey.pem'])
            cert = proxy.execute(['cat', '/etc/letsencrypt/live/' + self.fulldomain + '/fullchain.pem'])
            self.write({'cert_key': key, 'cert_cert': cert, 'cert_renewal_date': (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")})
            proxy.execute([
                'rm',
                '/etc/nginx/sites-enabled/' + self.fullname])
            proxy.execute(['rm', self.nginx_configfile])
            proxy.execute(['/etc/init.d/nginx', 'reload'])
            proxy.execute(['rm -rf ' + webroot])
            proxy_link.deploy_link()
        return res

    @api.multi
    def renew_cert(self):
        res = super(ClouderBase, self).renew_cert()
        link_obj = self.env['clouder.base.link']
        proxy_links = link_obj.search([('base_id','=',self.id),('name.name.type_id.name','=','proxy'),('target','!=',False)])
        if proxy_links:
            proxy_link = proxy_links[0]
            proxy = proxy_link.target
            proxy.execute([
                'echo', '"' + self.cert_cert + '"', '>', '/etc/letsencrypt/live/' + self.fulldomain + '/fullchain.pem'
            ])
            proxy.execute([
                'echo', '"' + self.cert_key + '"', '>', '/etc/letsencrypt/live/' + self.fulldomain + '/privkey.pem'])
            proxy.execute(['/opt/letsencrypt/letsencrypt-auto renew --force-renew'])
            key = proxy.execute(['cat', '/etc/letsencrypt/live/' + self.fulldomain + '/privkey.pem'])
            cert = proxy.execute(['cat', '/etc/letsencrypt/live/' + self.fulldomain + '/fullchain.pem'])
            self.write({'cert_key': key, 'cert_cert': cert, 'cert_renewal_date': (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")})
        return res



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
            if self.base_id.is_root:
                target.send(
                    modules.get_module_path(
                        'clouder_template_proxy'
                    ) + '/res/proxy-root.config', self.base_id.nginx_configfile + '-root')
                target.execute(['cat', self.base_id.nginx_configfile + '-root', '>>',  self.base_id.nginx_configfile])
                target.execute(['rm', self.base_id.nginx_configfile + '-root'])
            target.execute([
                'sed', '-i', '"s/BASE/' + self.base_id.name + '/g"',
                self.base_id.nginx_configfile])
            target.execute([
                'sed', '-i', '"s/DOMAIN/' + self.base_id.fulldomain +
                '/g"', self.base_id.nginx_configfile])
            target.execute([
                'sed', '-i', '"s/SERVER/' +
                self.base_id.container_id.server_id.name + '/g"',
                self.base_id.nginx_configfile])
            if 'http' in self.base_id.container_id.ports:
                target.execute([
                    'sed', '-i', '"s/PORT/' +
                    self.base_id.container_id.ports['http']['hostport'] +
                    '/g"', self.base_id.nginx_configfile])
            # self.deploy_prepare_apache(cr, uid, vals, context)
            cert_file = '/etc/ssl/certs/' + self.base_id.fulldomain + '.crt'
            key_file = '/etc/ssl/private/' + self.base_id.fulldomain + '.key'
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
                'rm', '/etc/ssl/certs/' + self.base_id.fulldomain + '.*'])
            target.execute([
                'rm', '/etc/ssl/private/' + self.base_id.fulldomain + '.*'])
            target.execute(['/etc/init.d/nginx', 'reload'])
