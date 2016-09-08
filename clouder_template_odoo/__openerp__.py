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

{
    'name': 'Clouder Template Odoo',
    'version': '1.0',
    'category': 'Clouder',
    'depends': [
        'clouder_template_bind',
        'clouder_template_gitlab',
        'clouder_template_shinken',
        'clouder_template_postfix',
        'clouder_template_proxy',
        'clouder_template_postgres',
        'clouder_template_piwik'
    ],
    'author': 'Yannick Buron (Clouder)',
    'license': 'Other OSI approved licence',
    'website': 'https://github.com/clouder-community/clouder',
    'description': """
    Clouder Odoo
    """,
    'demo': [],
    'data': [
        'template.xml'
    ],
    'installable': True,
    'application': True,
}
