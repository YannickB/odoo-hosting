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

import openerp.addons.saas.execute as execute

import logging
_logger = logging.getLogger(__name__)


class saas_base_link(osv.osv):
    _inherit = 'saas.base.link'

    def deploy_piwik(self, cr, uid, vals, piwik_id, context={}):
        super(saas_base_link, self).deploy_piwik(cr, uid, vals, piwik_id, context=context)
        if vals['link_target_app_code'] == 'piwik' and vals['apptype_name'] == 'drupal':
            ssh, sftp = execute.connect(vals['container_fullname'], context=context)
            execute.execute(ssh, ['drush', 'variable-set', 'piwik_site_id', piwik_id], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            execute.execute(ssh, ['drush', 'variable-set', 'piwik_url_http', 'http://' +  vals['link_target_base_fulldomain'] + '/'], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            execute.execute(ssh, ['drush', 'variable-set', 'piwik_url_https', 'https://' +  vals['link_target_base_fulldomain'] + '/'], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            execute.execute(ssh, ['drush', 'variable-set', 'piwik_privacy_donottrack', '0'], context, path=vals['service_full_localpath_files'] + '/sites/' + vals['base_fulldomain'])
            ssh.close()
            sftp.close()
        return