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
import paramiko
import execute

import logging
_logger = logging.getLogger(__name__)


class saas_save_repository(osv.osv):
    _inherit = 'saas.save.repository'

    def purge(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['bup_fullname'], context=context)
        execute.execute(ssh, ['git', '--git-dir=/home/bup/.bup', 'branch', '-D', vals['saverepo_name']], context)
        ssh.close()
        sftp.close()


        return

class saas_save_save(osv.osv):
    _inherit = 'saas.save.save'

    def deploy(self, cr, uid, vals, context={}):
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})
        ssh, sftp = execute.connect(vals['saverepo_container_server'], 22, 'root', context)
        execute.execute(ssh, ['docker', 'run', '-t', '--rm', '--volumes-from', vals['saverepo_container_name'], '-v', '/opt/keys/bup:/root/.ssh', 'img_bup:latest', '/opt/save', vals['saverepo_name'], str(int(vals['save_now_epoch'])), vals['save_container_volumes']], context)
        ssh.close()
        sftp.close()


        return

class saas_config_settings(osv.osv):
    _inherit = 'saas.config.settings'

    def cron_upload_save(self, cr, uid, ids, context={}):
        container_obj = self.pool.get('saas.container')
        context.update({'saas-self': self, 'saas-cr': cr, 'saas-uid': uid})

        container_ids = container_obj.search(cr, uid, [], context=context)
        context['container_save_comment'] = 'Save before upload_save'
        container_obj.save(cr, uid, container_ids, context=context)

        vals = self.get_vals(cr, uid, context=context)

        ssh, sftp = execute.connect(vals['bup_fullname'], username='bup', context=context)
        execute.execute(ssh, ['bup', 'fsck', '-g'], context)
        execute.execute(ssh, ['bup', 'fsck', '-r'], context)
        execute.execute(ssh, ['tar', 'czf', '/home/bup/bup.tar.gz', '-C', '/home/bup/.bup', '.'], context)
        execute.execute(ssh, ['/opt/upload', vals['config_ftpuser'], vals['config_ftppass'], vals['config_ftpserver']], context)
        execute.execute(ssh, ['rm', '/home/bup/bup.tar.gz'], context)
        ssh.close()
        sftp.close()


        ssh, sftp = execute.connect(vals['shinken_fullname'], context=context)
        execute.execute(ssh, ['rm', '-rf', '/opt/control-bup'], context)
        execute.execute(ssh, ['mkdir', '-p', '/opt/control-bup/bup'], context)
        execute.execute(ssh, ['ncftpget', '-u', vals['config_ftpuser'], '-p' + vals['config_ftppass'], vals['config_ftpserver'], '/opt/control-bup', '/bup.tar.gz'], context)
        execute.execute(ssh, ['tar', '-xf', '/opt/control-bup/bup.tar.gz', '-C', '/opt/control-bup/bup'], context)

        for container in container_obj.browse(cr, uid, container_ids, context=context):
            container_vals = container_obj.get_vals(cr, uid, container.id, context=context)
            execute.execute(ssh, ['export BUP_DIR=/opt/control-bup/bup; bup restore -C /opt/control-bup/restore/' + container_vals['container_fullname'] + ' ' + container_vals['saverepo_name'] + '/latest'], context)
        execute.execute(ssh, ['chown', '-R', 'shinken:shinken', '/opt/control-bup'], context)
        ssh.close()
        sftp.close()
