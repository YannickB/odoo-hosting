# -*- coding: utf-8 -*-
# Copyright 2015 Clouder SASU
# License LGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import string
from random import SystemRandom


def generate_random_password(size, punctuation=False):
    """ Method which can be used to generate a random password.

    :param size: (int) The size of the random string to generate
    :param punctuation: (bool) Allow punctuation in the password
    :return: (str) Psuedo-random string
    """
    choice = SystemRandom().choice
    chars = '%s%s%s' % (
        string.letters, string.digits,
        punctuation and string.punctuation or '',
    )
    return ''.join(choice(chars) for _ in xrange(size))
