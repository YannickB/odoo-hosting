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


class ClouderContainer(models.Model):
    """
    Add methods to manage the redis specificities.
    """

    _inherit = 'clouder.container'

    @api.multi
    def deploy_post(self):
        super(ClouderContainer, self).deploy_post()

        # if self.application_id.type_id.name == 'redis':
        #     self.execute(
        #                  ['apt-get', '-qq', 'update',],
        #                  path='/', username='redis')
        #     self.execute(['apt-get', '-y', 'redis-server'],
        #                  path='/', username='redis')
        #     self.execute(['/bin/bash', './res/configure_redis.sh'],
        #                  path='/', username='redis')

