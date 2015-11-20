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
import erppeek


class ClouderServer(models.Model):
    """
    Add methods to manage the postgres specificities.
    """

    _inherit = 'clouder.server'

    @api.multi
    def oneclick_clouder_deploy(self):
        self = self.with_context(no_enqueue=True)

        image_obj = self.env['clouder.image']
        image = image_obj.search([('name','=','img_registry')])
        image.build()

        image = image_obj.search([('name','=','img_backup')])
        image.build()

        image = image_obj.search([('name','=','img_postfix')])
        image.build()

        image = image_obj.search([('name','=','img_bind')])
        image.build()

        image = image_obj.search([('name','=','img_proxy')])
        image.build()

        image = image_obj.search([('name','=','img_shinken')])
        image.build()

        image = image_obj.search([('name','=','img_postgres')])
        image.build()

        image = image_obj.search([('name','=','img_odoo_data')])
        image.build()

        image = image_obj.search([('name','=','img_odoo_files8')])
        image.build()

        image = image_obj.search([('name','=','img_odoo_exec')])
        image.build()

        container_obj = self.env['clouder.container']
        application_obj = self.env['clouder.application']

        application = application_obj.search(['code','=','registry'])
        container_obj.create({
            'name': 'registry',
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search(['code','=','backup-bup'])
        container_obj.create({
            'name': 'backup',
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search(['code','=','postfix'])
        container_obj.create({
            'name': 'postfix',
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search(['code','=','bind'])
        bind = container_obj.create({
            'name': 'bind',
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search(['code','=','proxy'])
        container_obj.create({
            'name': 'proxy',
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search(['code','=','shinken'])
        container_obj.create({
            'name': 'shinken',
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search(['code','=','postgres'])
        container_obj.create({
            'name': 'postgres',
            'server_id': self.id,
            'application_id': application.id,
        })

        application = application_obj.search(['code','=','clouder'])
        clouder = container_obj.create({
            'name': 'clouder',
            'server_id': self.id,
            'application_id': application.id,
            'subservice_name': 'test'
        })

        domain_obj = self.env['clouder.domain']
        domain = domain_obj.create({
            'name': 'mydomain',
            'dns_id': bind.id
        })

        base_obj = self.env['clouder.base']
        application = application_obj.search(['code','=','clouder'])
        base_obj.create({
            'name': clouder,
            'domain_id': domain.id,
            'application_id': application.id,
            'admin_name': 'admin',
            'admin_password': 'admin',
            'test': True
        })

        clouder.install_subservice()


    @api.multi
    def oneclick_clouder_purge(self):

        self = self.with_context(no_enqueue=True)

        container_obj = self.env['clouder.container']

        container_obj.search([('name','=','clouder-dev')]).unlink()

        container_obj.search([('name','=','clouder')]).unlink()

        self.env['clouder.domain'].search([('name','=','mydomain')]).unlink()

        container_obj.search([('name','=','postgres')]).unlink()

        container_obj.search([('name','=','shinken')]).unlink()

        container_obj.search([('name','=','proxy')]).unlink()

        container_obj.search([('name','=','bind')]).unlink()

        container_obj.search([('name','=','postfix')]).unlink()

        container_obj.search([('name','=','backup')]).unlink()

        container_obj.search([('name','=','registry')]).unlink()