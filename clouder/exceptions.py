# -*- coding: utf-8 -*-
# Copyright 2016 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).


try:
    from odoo.exceptions import ValidationError
except ImportError:
    from openerp.exceptions import ValidationError


class ClouderError(ValidationError):
    """ It provides an error containing Clouder specific logic

    Attributes:
        model_obj: (clouder.model.ClouderModel) Clouder model instance that
            trigger this error
    """

    def __init__(self, model_obj, message):
        """ It throws error, stores the model_obj for use, and issues log
        :param model_obj: (clouder.model.ClouderModel) Clouder model object
            that is triggering the exception
        :param message: (str) Message to throw and log
        :raises: (ClouderError) Exception after generating appropriate log
        """
        try:
            model_obj.log('Raising error: "%s"' % message)
            model_obj.log('Version: "%s"' % model_obj.version)
        except AttributeError:
            # Model does not _inherit `clouder.model`
            pass
        self.model_obj = model_obj
        super(ClouderError, self).__init__(message)
