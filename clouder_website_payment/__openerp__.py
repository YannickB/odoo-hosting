# -*- coding: utf-8 -*-
##############################################################################
#
# Author: Yannick Buron, Nicolas Petit
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

{
    'name': 'Clouder Website Payment',
    'version': '1.0',
    'category': 'Clouder',
    'depends': ['clouder_website', 'payment', 'clouder_invoicing'],
    'author': 'Yannick Buron (Clouder), Nicolas Petit',
    'license': 'Other OSI approved licence',
    'website': 'https://github.com/clouder-community/clouder',
    'description': """
    Add payment capabilities to the external form generated in Clouder Website
    """,
    'demo': [],
    'data': [
        'templates.xml',
        'clouder_website_payment_data.xml',
        'clouder_website_payment_view.xml'
    ],
    'installable': True,
    'application': True,
}
