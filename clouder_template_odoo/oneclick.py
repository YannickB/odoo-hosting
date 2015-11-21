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
    def oneclick_clouder_deploy(self):
        self = self.with_context(no_enqueue=True)#, container_ports={'nginx':80,'nginx-ssl':443,'bind':53})
        prefix = self.oneclick_prefix

        image_obj = self.env['clouder.image']

        # image = image_obj.search([('name','=','img_registry')])
        # image.build()

        container_obj = self.env['clouder.container']
        application_obj = self.env['clouder.application']

        # application = application_obj.search([('code','=','registry')])
        # registry = container_obj.create({
        #     'name': prefix + '-registry',
        #     'server_id': self.id,
        #     'application_id': application.id,
        # })

        #
        # image = image_obj.search([('name','=','img_backup')])
        # image.registry_id = registry.id
        # image.build()
        #
        # image = image_obj.search([('name','=','img_postfix')])
        # image.registry_id = registry.id
        # image.build()
        #
        # image = image_obj.search([('name','=','img_bind')])
        # image.registry_id = registry.id
        # image.build()
        #
        # image = image_obj.search([('name','=','img_proxy')])
        # image.registry_id = registry.id
        # image.build()
        #
        # image = image_obj.search([('name','=','img_shinken')])
        # image.registry_id = registry.id
        # image.build()
        #
        # image = image_obj.search([('name','=','img_postgres')])
        # image.registry_id = registry.id
        # image.build()
        #
        # image = image_obj.search([('name','=','img_odoo_data')])
        # image.registry_id = registry.id
        # image.build()
        #
        # image = image_obj.search([('name','=','img_odoo_files8')])
        # image.registry_id = registry.id
        # image.build()
        #
        # image = image_obj.search([('name','=','img_odoo_exec')])
        # image.registry_id = registry.id
        # image.build()
        #
        # application = application_obj.search([('code','=','backup-bup')])
        # container_obj.create({
        #     'name': prefix + '-backup',
        #     'server_id': self.id,
        #     'application_id': application.id,
        # })
        #
        # application = application_obj.search([('code','=','postfix')])
        # container_obj.create({
        #     'name': prefix + '-postfix',
        #     'server_id': self.id,
        #     'application_id': application.id,
        # })
        #
        # application = application_obj.search([('code','=','bind')])
        # bind = container_obj.create({
        #     'name': prefix + '-bind',
        #     'server_id': self.id,
        #     'application_id': application.id,
        # })
        #
        # application = application_obj.search([('code','=','proxy')])
        # container_obj.create({
        #     'name': prefix + '-proxy',
        #     'server_id': self.id,
        #     'application_id': application.id,
        # })
        #
        # application = application_obj.search([('code','=','shinken')])
        # container_obj.create({
        #     'name': prefix + '-shinken',
        #     'server_id': self.id,
        #     'application_id': application.id,
        # })
        #
        # application = application_obj.search([('code','=','postgres')])
        # container_obj.create({
        #     'name': prefix + '-postgres',
        #     'server_id': self.id,
        #     'application_id': application.id,
        # })
        #
        # application = application_obj.search([('code','=','clouder')])
        # clouder = container_obj.create({
        #     'name': prefix + '-clouder',
        #     'server_id': self.id,
        #     'application_id': application.id,
        #     'subservice_name': 'test'
        # })

        domain_obj = self.env['clouder.domain']
        # domain = domain_obj.create({
        #     'name': 'mydomain',
        #     'organisation': 'My Company',
        #     'dns_id': bind.id
        # })
        #
        domain = domain_obj.search([('name','=','mydomain')])  #####
        clouder = container_obj.search([('name','=',prefix + '-clouder')])  #####
        base_obj = self.env['clouder.base']
        application = application_obj.search([('code','=','clouder')])
        base_obj.create({
            'name': 'clouder',
            'domain_id': domain.id,
            'title': 'My Clouder',
            'application_id': application.id,
            'container_id': clouder.id,
            'admin_name': 'admin',
            'admin_password': 'admin',
            'test': True
        })
        #
        # clouder.install_subservice()


    @api.multi
    def oneclick_clouder_purge(self):
        return

        # self = self.with_context(no_enqueue=True)
        # prefix = self.oneclick_prefix
        #
        # container_obj = self.env['clouder.container']
        #
        # container_obj.search([('name','=', prefix + '-clouder-test')]).unlink()
        #
        # container_obj.search([('name','=',prefix + '-clouder')]).unlink()
        #
        # self.env['clouder.domain'].search([('name','=','mydomain')]).unlink()
        #
        # container_obj.search([('name','=',prefix + '-postgres')]).unlink()
        #
        # container_obj.search([('name','=',prefix + '-shinken')]).unlink()
        #
        # container_obj.search([('name','=',prefix + '-proxy')]).unlink()
        #
        # container_obj.search([('name','=',prefix + '-bind')]).unlink()
        #
        # container_obj.search([('name','=',prefix + '-postfix')]).unlink()
        #
        # container_obj.search([('name','=',prefix + '-backup')]).unlink()
        #
        # container_obj.search([('name','=',prefix + '-registry')]).unlink()