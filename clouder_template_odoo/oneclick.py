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

from openerp import models, api, modules


class ClouderServer(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.server'

    @api.multi
    def oneclick_deploy_element(self, type, code, container=False, domain=False):

        application_obj = self.env['clouder.application']
        container_obj = self.env['clouder.container']
        base_obj = self.env['clouder.base']

        application = application_obj.search([('code', '=', code)])

        if type == 'container':
            if not container_obj.search([('environment_id', '=', self.environment_id.id), ('suffix', '=', code)]):
                container = container_obj.create({
                    'suffix': code,
                    'environment_id': self.environment_id.id,
                    'server_id': self.id,
                    'application_id': application.id,
                })
                return container

        if type == 'base':
            if not base_obj.search([('name', '=', code), ('domain_id', '=', domain.id)]):
                base = base_obj.create({
                    'name': code,
                    'domain_id': domain.id,
                    'environment_id': self.environment_id.id,
                    'title': application.name,
                    'application_id': application.id,
                    'container_id': container.id,
                    'admin_name': 'admin',
                    'admin_password': 'admin',
                })
                return base


    @api.multi
    def oneclick_clouder_deploy(self):
        self = self.with_context(no_enqueue=True)
        # TODO
        # container_ports={'nginx':80,'nginx-ssl':443,'bind':53})

        image_obj = self.env['clouder.image']
        image_version_obj = self.env['clouder.image.version']

        port_obj = self.env['clouder.container.port']
        base_obj = self.env['clouder.base']
        application_obj = self.env['clouder.application']

        self.oneclick_deploy_element('container', 'backup-bup')

        self.oneclick_deploy_element('container', 'spamassassin')

        ports = []
        if self.oneclick_ports:
            ports = [(0,0,{'name':'postfix', 'localport': 25, 'hostport': 25, 'expose': 'internet'})]
        postfix = self.oneclick_deploy_element('container', 'postfix')
        if self.oneclick_ports:
            port = port_obj.search([('container_id', '=', postfix.id),('name','=','postfix')])
            port.write({'hostport': 25})
            postfix.reinstall()

        ports = []
        if self.oneclick_ports:
            ports = [(0,0,{'name':'bind', 'localport': 53, 'hostport': 53, 'expose': 'internet', 'udp': True})]
        bind = self.oneclick_deploy_element('container', 'bind')
        if self.oneclick_ports:
            port = port_obj.search([('container_id', '=', bind.id),('name','=','bind')])
            port.write({'hostport': 53})
            bind.reinstall()

        domain_obj = self.env['clouder.domain']
        domain = domain_obj.create({
            'name': self.oneclick_domain,
            'organisation': self.oneclick_domain,
            'dns_id': bind.id
        })

        ports = []
        if self.oneclick_ports:
            ports = [(0,0,{'name':'nginx', 'localport': 80, 'hostport': 80, 'expose': 'internet'}),
                     (0,0,{'name':'nginx-ssl', 'localport': 443, 'hostport': 443, 'expose': 'internet'})]
        proxy = self.oneclick_deploy_element('container', 'proxy')
        if self.oneclick_ports:
            port = port_obj.search([('container_id', '=', proxy.id),('name','=','nginx')])
            port.write({'hostport': 80})
            port = port_obj.search([('container_id', '=', proxy.id),('name','=','nginx-ssl')])
            port.write({'hostport': 443})
            proxy.reinstall()

        container = self.oneclick_deploy_element('container', 'shinken')
        self.oneclick_deploy_element('base', 'shinken', container=container, domain=domain)

        self.oneclick_deploy_element('container', 'glances')

        container = self.oneclick_deploy_element('container', 'registry')
        self.oneclick_deploy_element('base', 'registry', container=container, domain=domain)

        self.oneclick_deploy_element('container', 'postgres')

        self.oneclick_deploy_element('container', 'redis')

        container = self.oneclick_deploy_element('container', 'gitlab')
        self.oneclick_deploy_element('base', 'shinken', container=container, domain=domain)

        self.oneclick_deploy_element('container', 'gitlabci')

        container = self.oneclick_deploy_element('container', 'clouder9')
        self.oneclick_deploy_element('base', 'clouder9', container=container, domain=domain)

#        container.install_subservice()

    @api.multi
    def oneclick_clouder_purge(self):
        self = self.with_context(no_enqueue=True)

        container_obj = self.env['clouder.container']

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'clouder-test')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'clouder9')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'gitlabci')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'gitlab')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'redis')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'postgres')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'registry')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'glances')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'shinken')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'proxy')]).unlink()

        self.env['clouder.domain'].search([('name', '=', self.oneclick_domain)]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'bind')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'postfix')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'spamassassin')]).unlink()

        container_obj.search([('environment_id', '=', self.environment_id.id),
                              ('suffix', '=', 'backup-bup')]).unlink()
