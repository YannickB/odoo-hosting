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

# from openerp.addons.connector.queue.job \
#     import _unpickle, job, Job, OpenERPJobStorage
# from openerp.addons.connector.queue import worker
#
# import logging
# _logger = logging.getLogger(__name__)

#
# def perform(self, session):
#     """ Execute the job.
#
#     The job is executed with the user which has initiated it.
#
#     :param session: session to execute the job
#     :type session: ConnectorSession
#     """
#     assert not self.canceled, "Canceled job"
#     with session.change_user(self.user_id):
#         self.retry += 1
#         try:
#             ############
#             with session.change_context({'job_uuid': self._uuid}):
#                 self.result = self.func(session, *self.args, **self.kwargs)
#             ############
#         except RetryableJobError as err:
#             if err.ignore_retry:
#                 self.retry -= 1
#                 raise
#             elif not self.max_retries:  # infinite retries
#                 raise
#             elif self.retry >= self.max_retries:
#                 type_, value, traceback = sys.exc_info()
#                 # change the exception type but keep the original
#                 # traceback and message:
#                 #http://blog.ianbicking.org/2007/09/12/re-raising-exceptions/
#                 new_exc = FailedJobError("Max. retries (%d) reached: %s" %
#                                          (self.max_retries, value or type_)
#                                          )
#                 raise new_exc.__class__, new_exc, traceback
#             raise
#     return self.result
