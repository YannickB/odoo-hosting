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


from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.queue import worker

import os

import logging
_logger = logging.getLogger(__name__)



#
# class QueueJob(models.Model):
#
#     _inherit = 'queue.job'
#
#
#
# rajout champs
# rajouter un champ fonction/property qui va chercher les job prioritaires

#question pour nico : j'ai une classe (pas une classe openerp) definie dans le module connector, avec une fonction a l'interieur.
# Est-ce que j'ai moyen de surcharger dans mon module cette fonction de sorte que mon code qui surcharge soit appellé même si c'est le module connecteur qui appelle cette fonction, sans toucher le code du connecteur?


class ClouderWorker(worker.Worker):
    """ Post and retrieve jobs from the queue, execute them"""

    def run_job(self, job):
        """ Execute a job """
        #si y'a des fonction prioritaires on return et on rajoute 1 de priorité en plus par rapport a la priorité la plus haute des fonctions prioritaires
        #super
        _logger.info('=======OK WORKER======')
        return super(ClouderWorker, self).run_job(job)




#
# class Job(object):
#
#     def perform(self, session):
#         _logger.info('=======OK JOB======')
#         return super(Worker, self).perform(session)
#         #
#         # super
#         # mettre a jour log


class ClouderWatcher(worker.WorkerWatcher):

    def _new(self, db_name):
        _logger.info('=======OK WATCHER======')
        """ Create a new worker for the database """
        if db_name in self._workers:
            raise Exception('Database %s already has a worker (%s)' %
                            (db_name, self._workers[db_name].uuid))
        worker = ClouderWorker(db_name, self)
        self._workers[db_name] = worker
        worker.daemon = True
        worker.start()


class QueueWorker(models.Model):
    """ Worker """
    _inherit = 'queue.worker'

    @api.model
    def enqueue_jobs(self):
        """ Enqueue all the jobs assigned to the worker of the current
        process
        """
        worker = ClouderWatcher().worker_for_db(self.env.cr.dbname)
        if worker:
            self._enqueue_jobs()
        else:
            _logger.debug('No worker started for process %s', os.getpid())
        return True

    def _enqueue_jobs(self):
        """ Add to the queue of the worker all the jobs not
        yet queued but already assigned."""
        job_model = self.env['queue.job']
        _logger.info('=======OK QUEUEWORKER======')
        try:
            db_worker_id = self._worker().id
        except AssertionError as e:
            _logger.exception(e)
            return
        jobs = job_model.search([('worker_id', '=', db_worker_id),
                                 ('state', '=', 'pending')],
                                )
        worker = ClouderWatcher().worker_for_db(self.env.cr.dbname)
        for job in jobs:
            worker.enqueue_job_uuid(job.uuid)