# -*- coding: utf-8 -*-
##############################################################################
#
# Author: Yannick Buron
# Copyright 2015, TODAY Clouder SASU
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License
#  as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# with this program. If not, see
# <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, tools
import logging
import copy_reg

from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import\
    job, whitelist_unpickle_global

_logger = logging.getLogger(__name__)


@job
def connector_enqueue(
        session, model_name, record_id, func_name,
        action, job_id, context, *args, **kargs):

    context = context.copy()
    context.update(session.env.context.copy())
    with session.change_context(context):
        record = session.env[model_name].browse(record_id)

    job = record.env['queue.job'].search([
        ('uuid', '=', record.env.context['job_uuid'])])
    clouder_jobs = record.env['clouder.job'].search([('job_id', '=', job.id)])
    clouder_jobs.write({'log': False})
    job.env.cr.commit()

    priority = record.control_priority()
    if priority:
        job.write({'priority': priority + 1})
        job.env.cr.commit()
        session.env[model_name].raise_error(
            "Waiting for another job to finish",
        )

    res = getattr(record, func_name)(action, job_id, *args, **kargs)
    # if 'clouder_unlink' in record.env.context:
    #     res = super(ClouderModel, record).unlink()
    record.log('===== END JOB ' + session.env.context['job_uuid'] + ' =====')
    job.search([('state', '=', 'failed')]).write({'state': 'pending'})
    return res

# Add function in connector whitelist
whitelist_unpickle_global(copy_reg._reconstructor)
whitelist_unpickle_global(tools.misc.frozendict)
whitelist_unpickle_global(dict)
whitelist_unpickle_global(connector_enqueue)


class ClouderJob(models.Model):
    """
    """

    _inherit = 'clouder.job'

    job_id = fields.Many2one('queue.job', 'Connector Job')
    job_state = fields.Selection([
        ('pending', 'Pending'),
        ('enqueud', 'Enqueued'),
        ('started', 'Started'),
        ('done', 'Done'),
        ('failed', 'Failed')], 'Job State',
        related='job_id.state', readonly=True)


class ClouderModel(models.AbstractModel):
    """
    """

    _inherit = 'clouder.model'

    @api.multi
    def enqueue(self, name, action, clouder_job_id):
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=self.env.context)
        job_uuid = connector_enqueue.delay(
            session, self._name, self.id, 'do_exec', action, clouder_job_id,
            self.env.context, description=name,
            max_retries=0)
        job_id = self.env['queue.job'].search([('uuid', '=', job_uuid)])[0]
        clouder_job = self.env['clouder.job'].browse(clouder_job_id)
        clouder_job.write({'job_id': job_id.id})
