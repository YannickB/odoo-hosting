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
    def oneclick_deploy_element(self, type, code, container=False, domain=False, ports=[]):

        application_obj = self.env['clouder.application']
        container_obj = self.env['clouder.container']
        port_obj = self.env['clouder.container.port']
        base_obj = self.env['clouder.base']

        application = application_obj.search([('code', '=', code)])

        if type == 'container':
            container = container_obj.search([('environment_id', '=', self.environment_id.id), ('suffix', '=', code)])
            if not container:
                # ports = []
                # if self.oneclick_ports:
                #     ports = [(0,0,{'name':'bind', 'localport': 53, 'hostport': 53, 'expose': 'internet', 'udp': True})]
                container = container_obj.create({
                    'suffix': code,
                    'environment_id': self.environment_id.id,
                    'server_id': self.id,
                    'application_id': application.id,
                })
                if self.oneclick_ports and ports:
                    for port in ports:
                        port_record = port_obj.search([('container_id', '=', container.id),('localport','=',port)])
                        port_record.write({'hostport': port})
                    container.reinstall()
            return container

        if type == 'base':
            base = base_obj.search([('name', '=', code), ('domain_id', '=', domain.id)])
            if not base:
                base = base_obj.create({
                    'name': code,
                    'domain_id': domain.id,
                    'environment_id': self.environment_id.id,
                    'title': application.name,
                    'application_id': application.id,
                    'container_id': container.id,
                    'admin_name': 'admin',
                    'admin_password': 'adminadmin',
                })
            return base


    @api.multi
    def oneclick_clouder_deploy(self):
        self = self.with_context(no_enqueue=True)

        self.oneclick_deploy_element('container', 'backup-bup')

        self.oneclick_deploy_element('container', 'spamassassin')

        self.oneclick_deploy_element('container', 'postfix', ports=[25])

        bind = self.oneclick_deploy_element('container', 'bind', ports=[53])

        domain_obj = self.env['clouder.domain']
        domain = domain_obj.search([('name', '=', self.oneclick_domain)])
        if not domain:
            domain = domain_obj.create({
                'name': self.oneclick_domain,
                'organisation': self.oneclick_domain,
                'dns_id': bind.id
            })

        self.oneclick_deploy_element('container', 'proxy', ports=[80, 443])

        container = self.oneclick_deploy_element('container', 'shinken')
        self.oneclick_deploy_element('base', 'shinken', container=container, domain=domain)

        container = self.oneclick_deploy_element('container', 'registry')
        self.oneclick_deploy_element('base', 'registry', container=container, domain=domain)

        self.oneclick_deploy_element('container', 'postgres')

        self.oneclick_deploy_element('container', 'redis')

        container = self.oneclick_deploy_element('container', 'gitlab')
        self.oneclick_deploy_element('base', 'gitlab', container=container, domain=domain)

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
