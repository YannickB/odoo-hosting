# -*- coding: utf-8 -*-
##############################################################################
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


from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

import time
from datetime import datetime, timedelta
import subprocess
import re
import openerp.addons.saas.execute as execute

import logging
_logger = logging.getLogger(__name__)

class saas_application(osv.osv):
    _inherit = 'saas.application'


class saas_application_version(osv.osv):
    _inherit = 'saas.application.version'

    def build_application(self, cr, uid, vals, context):
        super(saas_application_version, self).build_application(cr, uid, vals, context)
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        if vals['apptype_name'] == 'drupal':
            execute.execute_write_file(vals['app_version_full_archivepath'] + '/drush.make', vals['app_buildfile'], context)
            execute.execute_local(['drush', 'make', vals['app_version_full_archivepath'] + '/drush.make', './'], context, path=vals['app_version_full_archivepath'])
            execute.execute_local(['cp', vals['config_conductor_path'] + '/saas/saas_drupal/res/wikicompare.script', vals['app_version_full_archivepath']], context)
            ssh, sftp = execute.connect('localhost', 22, 'saas-conductor', context)
            execute.execute(ssh, ['patch', '-p0', '-d', vals['app_version_full_archivepath'] + '/sites/all/modules/revisioning/', '<', vals['config_conductor_path'] + '/saas/saas_drupal/res/patch/revisioning_postgres.patch'], context)
            ssh.close()
            sftp.close()
            execute.execute_local(['mv', vals['app_version_full_archivepath'] + '/sites', vals['app_version_full_archivepath'] + '/sites-template'], context)
            execute.execute_local(['ln', '-s', '../sites', vals['app_version_full_archivepath'] + '/sites'], context)


    #
    # if [[ $name == 'dev' ]]
    # then
    # patch -p0 -d $archive_path/$app/${app}-${name}/archive/sites/all/themes/wikicompare_theme/ < $openerp_path/saas/saas/apps/drupal/patch/dev_zen_rebuild_registry.patch
    # fi


        return



    def get_current_version(self, cr, uid, obj, context=None):

        return False
