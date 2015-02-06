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
            ssh, sftp = execute.connect(vals['archive_fullname'], context=context)
            execute.execute(ssh, ['apt-get -qq update && DEBIAN_FRONTEND=noninteractive apt-get -y -qq install git php-pear'], context)
            execute.execute(ssh, ['pear channel-discover pear.drush.org'], context)
            execute.execute(ssh, ['pear install drush/drush'], context)
            execute.execute(ssh, ['echo "' + vals['app_buildfile'].replace('"', '\\"') + '" >> ' + vals['app_version_full_archivepath'] + '/drush.make'], context)
            execute.execute(ssh, ['drush', 'make', vals['app_version_full_archivepath'] + '/drush.make', './'], context, path=vals['app_version_full_archivepath'])
            sftp.put(vals['config_conductor_path'] + '/saas_drupal/res/wikicompare.script', vals['app_version_full_archivepath'] + '/wikicompare.script')
            sftp.put(vals['config_conductor_path'] + '/saas_drupal/res/patch/revisioning_postgres.patch', vals['app_version_full_archivepath'] + '/revisioning_postgres.patch')
            execute.execute(ssh, ['patch', '-p0', '-d', vals['app_version_full_archivepath'] + '/sites/all/modules/revisioning/', '<', vals['app_version_full_archivepath'] + '/revisioning_postgres.patch'], context)
            execute.execute(ssh, ['mv', vals['app_version_full_archivepath'] + '/sites', vals['app_version_full_archivepath'] + '/sites-template'], context)
            execute.execute(ssh, ['ln', '-s', '../sites', vals['app_version_full_archivepath'] + '/sites'], context)
            ssh.close()
            sftp.close()


    #
    # if [[ $name == 'dev' ]]
    # then
    # patch -p0 -d $archive_path/$app/${app}-${name}/archive/sites/all/themes/wikicompare_theme/ < $openerp_path/saas/saas/apps/drupal/patch/dev_zen_rebuild_registry.patch
    # fi


        return



    def get_current_version(self, cr, uid, obj, context=None):

        return False
