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


from openerp import models, api
import openerp.addons.clouder.clouder_model as clouder_model


class ClouderContainer(models.Model):
    """
    Add methods to manage the mysql container specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def deploy_post(self):
        """
        Update the root password after deployment.
        """
        super(ClouderContainer, self).deploy_post()

        if self.application_id.type_id.name == 'mysql':

            self.start()

            ssh = self.connect(self.fullname)
            self.execute(ssh, ['sed', '-i', '"/bind-address/d"',
                               '/etc/mysql/my.cnf'])
            if self.options['root_password']['value']:
                password = self.options['root_password']['value']
            else:
                password = clouder_model.generate_random_password(20)
                option_obj = self.env['clouder.container.option']
                options = option_obj.search([('container_id', '=', self),
                                             ('name', '=', 'root_password')])
                if options:
                    options.value = password
                else:
                    type_option_obj = self.env[
                        'clouder.application.type.option']
                    type_options = type_option_obj.search(
                        [('apptype_id.name', '=', 'mysql'),
                         ('name', '=', 'root_password')])
                    if type_options:
                        option_obj.create({'container_id': self,
                                           'name': type_options[0],
                                           'value': password})
            self.execute(ssh,
                         ['mysqladmin', '-u', 'root', 'password', password])
