# -*- coding: utf-8 -*-

import erppeek


def base_update(host, name, user, password):
    '''
    '''

    client = erppeek.Client(
        'http://' + host, db=name, user=user, password=password)
    client.upgrade('base')