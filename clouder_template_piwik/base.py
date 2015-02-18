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

import openerp.addons.clouder.execute as execute

import logging
_logger = logging.getLogger(__name__)


class clouder_base_link(osv.osv):
    _inherit = 'clouder.base.link'

    def deploy_piwik(self, cr, uid, vals, piwik_id, context={}):
        return

    def deploy_link(self, cr, uid, vals, context={}):
        super(clouder_base_link, self).deploy_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'piwik':
            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            piwik_id = execute.execute(ssh, ['mysql', vals['link_target_base_unique_name_'], '-h ' + vals['link_target_database_server'], '-u ' + vals['link_target_service_db_user'], '-p' + vals['link_target_service_db_password'], '-se',
                '"select idsite from piwik_site WHERE name = \'' + vals['base_fulldomain'] + '\' LIMIT 1;"'], context)
            if not piwik_id:
                execute.execute(ssh, ['mysql', vals['link_target_base_unique_name_'], '-h ' + vals['link_target_database_server'], '-u ' + vals['link_target_service_db_user'], '-p' + vals['link_target_service_db_password'], '-se',
                    '"INSERT INTO piwik_site (name, main_url, ts_created, timezone, currency) VALUES (\'' + vals['base_fulldomain'] + '\', \'http://' + vals['base_fulldomain'] + '\', NOW(), \'Europe/Paris\', \'EUR\');"'], context)
                piwik_id = execute.execute(ssh, ['mysql', vals['link_target_base_unique_name_'], '-h ' + vals['link_target_database_server'], '-u ' + vals['link_target_service_db_user'], '-p' + vals['link_target_service_db_password'], '-se',
                    '"select idsite from piwik_site WHERE name = \'' + vals['base_fulldomain'] + '\' LIMIT 1;"'], context)
#            execute.execute(ssh, ['mysql', vals['link_target_base_unique_name_'], '-h ' + vals['link_target_database_server'], '-u ' + vals['link_target_service_db_user'], '-p' + vals['link_target_service_db_password'], '-se',
#                '"INSERT INTO piwik_access (login, idsite, access) VALUES (\'anonymous\', ' + piwik_id + ', \'view\');"'], context)

            ssh.close()
            sftp.close()

            self.deploy_piwik(cr, uid, vals, piwik_id, context=context)

    def purge_link(self, cr, uid, vals, context={}):
        super(clouder_base_link, self).purge_link(cr, uid, vals, context=context)
        if vals['link_target_app_code'] == 'piwik':
            ssh, sftp = execute.connect(vals['link_target_container_fullname'], context=context)
            piwik_id = execute.execute(ssh, ['mysql', vals['link_target_base_unique_name_'], '-h ' + vals['link_target_database_server'], '-u ' + vals['link_target_service_db_user'], '-p' + vals['link_target_service_db_password'], '-se',
                '"select idsite from piwik_site WHERE name = \'' + vals['base_fulldomain'] + '\' LIMIT 1;"'], context)
            # if piwik_id:
            #     execute.execute(ssh, ['mysql', vals['link_target_base_unique_name_'], '-h ' + vals['link_target_database_server'], '-u ' + vals['link_target_service_db_user'], '-p' + vals['link_target_service_db_password'], '-se',
            #         '"DELETE FROM piwik_access WHERE idsite = ' + piwik_id + ';"'], context)

            ssh.close()
            sftp.close()