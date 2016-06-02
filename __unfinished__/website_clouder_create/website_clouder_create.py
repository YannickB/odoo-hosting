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

from openerp import models, fields, api, http, _
import os
import errno
import subprocess
import time
import logging

_logger = logging.getLogger(__name__)


class ClouderApplication(models.Model):
    """
    Adds information for web-creation on applications
    """

    _inherit = 'clouder.application'

    web_create_type = fields.Selection(
        [
            ('disabled', 'Disabled'),
            ('container', 'Container'),
            ('base', 'Base')
        ],
        'Web creation',
        default='disabled'
    )

    @api.multi
    def create_instance_from_request(self, data):
        """
        Creates a clouder container or base using provided data
        """
        """
        Pour Yannick:

        Données d'entrée:
            Un dictionnaire contenant les clefs suivantes:
                'clouder_partner_id': id du partenaire qui affiche le formulaire sur son site (entier),
                'prefix': le préfixe du domain (string),
                'application_id': id de l'application choisie (entier),
                'domain_id': id du domaine choisi (entier),
                'request_partner': partenaire contenant les infos remplies sur le formulaire (res.partner record)
        Cadeau:
            le code pour charger les ID
                application = self.browse(data['application_id'])
                domain = self.env['clouder.domain'].browse(data['domain_id'])
                clouder_partner = self.env['res.partner'].browse(data['clouder_partner_id'])
        """

        # TODO: implement
        _logger.info("\n\nCREATE INSTANCE DATA: {0}\n\n".format(data))

        # TODO: return newly created model
        return 0


class ClouderWebHelper(models.Model):
    """
    A class made to be called by widgets and webpages alike
    """
    _name = 'clouder.web.helper'

    @api.model
    def maintain_wsgi_server(self):
        """
        Checks that the server is running.

        Prints log and attempts reload if it's not the case.
        """

        def read_pid():
            """
            Reads the PID file for app_serv_form
            """
            pid_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'static',
                'src',
                'wsgi',
                'app_serve_form.pid'
            )
            try:
                pid_f = open(pid_path)
                pid = pid_f.read()
                pid_f.close()
                if not pid or pid == '\n':
                    return -1
                return int(pid)
            except ValueError, e:
                return -2
            except:
                return -99

        def check_running(pid):
            """
            Tries to send signal 0 to a process to see if it lives
            """
            try:
                os.kill(pid, 0)
                return True
            except OSError, err:
                if err.errno == errno.ESRCH:
                    # No process found
                    return False
                elif err.errno == errno.EPERM:
                    # No permissions, but the process is running
                    return True
                else:
                    # This should never happen: there is a problem and it should be checked
                    _logger.error("Unexpected exception while checking for process health")
                    raise err

        def relaunch():
            """
            Relaunch process
            """
            path_to_wsgi = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'static',
                'src',
                'wsgi',
                'app_serve_form.sh'
            )
            return subprocess.Popen([path_to_wsgi])

        # Check PID file
        proc_id = read_pid()

        # if invalid PID: relaunch
        if proc_id <= 0:
            if proc_id == -1:
                _logger.warning("WSGI server no PID - Relaunching.")
            elif proc_id == -2:
                _logger.warning("WSGI server unknown error with PID - Relaunching.")
            elif proc_id == -99:
                _logger.warning("WSGI server unknown error with PID - Relaunching.")
            relaunch()
            # Making sure the process had time to start before reading PID again
            time.sleep(5)
            proc_id = read_pid()

        # Check if PID is running
        if not check_running(proc_id):
            _logger.warning("WSGI PID exists but is not running. - Relaunching.")
            relaunch()

    @api.model
    def application_form_values(self):
        """
        Parses the values used in the form
        If data is not provided, creates default values for the form
        """
        app_orm = self.env['clouder.application'].sudo()
        domain_orm = self.env['clouder.domain'].sudo()
        country_orm = self.env['res.country'].sudo()
        state_orm = self.env['res.country.state'].sudo()

        applications = app_orm.search([('web_create_type', '!=', 'disabled')])
        domains = domain_orm.search([])
        countries = country_orm.search([])
        states = state_orm.search([])

        return {
            'applications': applications,
            'domains': domains,
            'countries': countries,
            'states': states,
        }

    @api.model
    def get_form_html(self):
        # Load file
        html_file = open(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'static',
            'src',
            'html',
            'template.html'
        ))
        html = u""
        for line in html_file:
            html += unicode(line+"\n")

        # Load data from odoo
        data = self.application_form_values()

        # Apply data to template
        # Applications
        options = u""
        for app in data['applications']:
            options += u"""<option value="{application.id}">{application.name}</option>""".format(application=app)
        html = html.replace("==CL_ADD_APPLICATION_OPTIONS==", options)

        # Domains
        options = u""
        for domain in data['domains']:
            options += u"""<option value="{domain.id}">{domain.name}</option>""".format(domain=domain)
        html = html.replace("==CL_ADD_DOMAIN_OPTIONS==", options)

        # Countries
        options = u""
        for country in data['countries']:
            options += u"""<option value="{country.id}">{country.name}</option>""".format(country=country)
        html = html.replace("==CL_ADD_COUNTRY_OPTIONS==", options)

        # States
        options = u""
        for state in data['states']:
            options += u"""<option value="{state.id}" country_id="{state.country_id.id}">
                {state.name}
            </option>""".format(state=state)
        html = html.replace("==CL_ADD_STATE_OPTIONS==", options)

        return html

    @api.model
    def submit_form(self, post_data):
        # Return codes:
        #   0: success
        #   1: mandatory field not set

        partner_mandatory_fields = [
            "name",
            "phone",
            "email",
            "street2",
            "city",
            "country_id"
        ]
        partner_optionnal_fields = [
            "street",
            "zip",
            "state_id"
        ]
        instance_mandatory_fields = [
            'application_id',
            'domain_id',
            'prefix',
            'clouder_partner_id'
        ]

        # Checking data
        partner_data = {}
        for mandat in partner_mandatory_fields:
            if mandat not in post_data:
                return {"code": 1, 'msg': 'Missing field "{0}"'.format(mandat)}
            partner_data[mandat] = post_data[mandat]
        for opt in partner_optionnal_fields:
            if opt in post_data:
                partner_data[opt] = post_data[opt]

        instance_data = {}
        for mandat in instance_mandatory_fields:
            if mandat not in post_data:
                return {"code": 1, 'msg': 'Missing field "{0}"'.format(mandat)}
            instance_data[mandat] = post_data[mandat]

        # All data retrieved, creating partner
        orm_partner = self.env['res.partner'].sudo()
        instance_data['request_partner'] = orm_partner.create(partner_data)

        # Parsing instance data
        instance_data['clouder_partner_id'] = int(instance_data['clouder_partner_id'])
        instance_data['application_id'] = int(instance_data['application_id'])
        instance_data['domain_id'] = int(instance_data['domain_id'])

        # Calling instance creation function
        orm_app = self.env['clouder.application'].sudo()
        orm_app.create_instance_from_request(instance_data)

        return {'code': 0, 'msg': 'Instance creation launched'}
