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
        """
        Loads the html template and fills-in the values before returning it
        """
        # Load template
        html = self.get_template()

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

    def get_template(self):
        """
        Returns the HTML form template with odoo-translated strings
        """
        # Return the template
        return \
            u"""<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
        <html>
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        <title>""" + _("Insert title here") + u"""</title>

        <style type="text/css">
        /* Elements */
        #TestOdooPlugin a
        {
            color: #428bca;
            text-decoration: none;
            background: transparent;
        }
        #TestOdooPlugin a:active, a:hover
        {
            outline: 0;
        }
        #TestOdooPlugin a:hover, a:focus
        {
            color: #2a6496;
            text-decoration: underline;
        }
        #TestOdooPlugin a:focus
        {
            outline: 5px auto -webkit-focus-ring-color;
            outline: thin dotted;
            outline-offset: -2px;
        }
        #TestOdooPlugin input
        {
            line-height: normal;
        }
        #TestOdooPlugin input[disabled]
        {
            cursor: default;
        }
        #TestOdooPlugin select
        {
            text-transform: none;
        }
        #TestOdooPlugin input, #TestOdooPlugin select
        {
            font-family: inherit;
            font-size: inherit;
            line-height: inherit;
            color: inherit;
            font: inherit;
            margin: 0;
        }
        #TestOdooPlugin label
        {
            display: inline-block;
            font-weight: bold;
            margin-bottom: 5px;
            max-width: 100%;
        }
        /* ID */
        #TestOdooPlugin #CF_Title
        {
            font-size: 36px;
            margin: .67em 0;
            color: inherit;
            font-family: inherit;
            font-weight: 500;
            line-height: 1.1;
            margin-bottom: 10px;
            margin-top: 20px;
        }

        /* Classes */
        #TestOdooPlugin .mb32
        {
            margin-bottom: 32px !important;
        }
        #TestOdooPlugin .pull-right
        {
            float: right !important;
            position: relative !important;
            right: 10px;
        }
        #TestOdooPlugin .pull-left
        {
            float: left !important;
            position: relative !important;
            left: 10px;
        }
        #TestOdooPlugin .btn:hover, #TestOdooPlugin .btn:focus, #TestOdooPlugin .btn:active,""" \
        + u"""#TestOdooPlugin .btn.active
        {
            background-color: #e6e6e6;
            border-color: #adadad;
            color: #333;
            background-color: #3071a9;
            border-color: #285e8e;
            color: #fff;
        }
        #TestOdooPlugin .btn:active, #TestOdooPlugin .btn.active
        {
            background-image: none;
        }
        #TestOdooPlugin .btn
        {
            background-image: none;
            border: 1px solid transparent;
            border-radius: 4px;
            cursor: pointer;
            display: inline-block;
            font-size: 14px;
            font-weight: normal;
            line-height: 1.42857143;
            margin-bottom: 0;
            moz-user-select: none;
            ms-user-select: none;
            padding: 6px 12px;
            text-align: center;
            user-select: none;
            vertical-align: middle;
            webkit-user-select: none;
            white-space: nowrap;
            background-color: #428bca;
            border-color: #357ebd;
            color: #fff;
        }
        #TestOdooPlugin .btn:focus, #TestOdooPlugin .btn:active:focus, #TestOdooPlugin .btn.active:focus
        {
            outline: 5px auto -webkit-focus-ring-color;
            outline: thin dotted;
            outline-offset: -2px;
        }
        #TestOdooPlugin .btn:hover, #TestOdooPlugin .btn:focus
        {
            color: #333;
            text-decoration: none;
        }
        #TestOdooPlugin .btn:active, #TestOdooPlugin .btn.active
        {
            background-image: none;
            box-shadow: inset 0 3px 5px rgba(0, 0, 0, .125);
            outline: 0;
            webkit-box-shadow: inset 0 3px 5px rgba(0, 0, 0, .125);
        }
        #TestOdooPlugin .form-control
        {
            background-color: #fff;
            background-image: none;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075);
            color: #555;
            display: inline-block;
            font-size: 14px;
            height: 34px;
            line-height: 1.42857143;
            o-transition: border-color ease-in-out .15s, box-shadow ease-in-out .15s;
            padding: 6px 12px;
            transition: border-color ease-in-out .15s, box-shadow ease-in-out .15s;
            webkit-box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075);
            webkit-transition: border-color ease-in-out .15s, -webkit-box-shadow ease-in-out .15s;
            width: 100%;
        }
        #TestOdooPlugin input[class="form-control"]
        {
            height: 20px;
        }
        #TestOdooPlugin select[class="form-control"]
        {
            width: 118%;
        }
        #TestOdooPlugin .form-control:focus
        {
            border-color: #66afe9;
            box-shadow: inset 0 1px 1px rgba(0,0,0,.075), 0 0 8px rgba(102, 175, 233, .6);
            outline: 0;
            webkit-box-shadow: inset 0 1px 1px rgba(0,0,0,.075), 0 0 8px rgba(102, 175, 233, .6);
        }
        #TestOdooPlugin .form-control::-moz-placeholder
        {
            color: #777;
            opacity: 1;
        }
        #TestOdooPlugin .form-control:-ms-input-placeholder
        {
            color: #777;
        }
        #TestOdooPlugin .form-control::-webkit-input-placeholder
        {
            color: #777;
        }
        #TestOdooPlugin .form-control[disabled], .form-control[readonly], fieldset[disabled] .form-control
        {
            background-color: #eee;
            cursor: not-allowed;
            opacity: 1;
        }
        #TestOdooPlugin .has-error .form-control
        {
            border-color: #a94442;
            box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075);
            webkit-box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075);
        }
        #TestOdooPlugin .has-error .form-control:focus
        {
            border-color: #843534;
            box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075), 0 0 6px #ce8483;
            webkit-box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075), 0 0 6px #ce8483;
        }
        #TestOdooPlugin .has-error .control-label
        {
            color: #a94442;
        }
        #TestOdooPlugin .col-lg-6
        {
            min-height: 1px;
            padding-left: 0px;
            padding-right: 25px;
            position: relative;
        }
        #TestOdooPlugin .clearfix:after, #TestOdooPlugin .form-group:after
        {
            clear: both;
        }
        #TestOdooPlugin .clearfix:before, #TestOdooPlugin .clearfix:after, #TestOdooPlugin .form-group:before,""" \
        + u"""#TestOdooPlugin .form-group:after
        {
            content: " ";
            display: table;
        }
        #TestOdooPlugin .clearfix:before, #TestOdooPlugin .clearfix:after
        {
            content: " ";
            display: table;
        }
        #TestOdooPlugin .form-group
        {
            margin-bottom: 15px;
            width: 40%;
        }
        #TestOdooPlugin .fa
        {
            display: inline-block;
            font: normal normal normal 14px/1 FontAwesome;
            font-family: FontAwesome !important;
            font-size: inherit;
            moz-osx-font-smoothing: grayscale;
            text-rendering: auto;
            webkit-font-smoothing: antialiased;
        }
        </style>

        </head>
        <body>
            <form id="ClouderForm" method="POST" action="">

                <input type="hidden" name="clouder_partner_id" value=""/>
                <input type="hidden" name="db" value=""/>

                <p class="CF_Title">""" + _("Request a Clouder Instance") + u"""</p>

                <fieldset class="CL_Step CL_Step1">
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="application_id">""" + _("Application") + u"""</label>
                        <select name="application_id" class="form-control">
                            <option value="">""" + _("Application...") + u"""</option>
                            ==CL_ADD_APPLICATION_OPTIONS==
                        </select>
                    </div>
                    <div class="clearfix"/>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="prefix">""" + _("Prefix") + u"""</label>
                        <input type="text" name="prefix" class="form-control"/>
                    </div>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="domain_id">""" + _("Domain Name") + u"""</label>
                        <select name="domain_id" class="form-control">
                            <option value="">""" + _("Domain...") + u"""</option>
                            ==CL_ADD_DOMAIN_OPTIONS==
                        </select>
                    </div>
                </fieldset>

                <fieldset class="CL_Step CL_Step2">
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="contact_name">""" + _("Your Name") + u"""</label>
                        <input type="text" name="name" class="form-control"/>
                    </div>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="street" style="font-weight: normal">""" \
                            + _("Company Name") \
                            + u"""</label>
                        <input type="text" name="street" class="form-control"/>
                    </div>
                    <div class="clearfix"/>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="contact_name">""" + _("Email") + u"""</label>
                        <input type="email" name="email" class="form-control"/>
                    </div>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="phone">""" + _("Phone") + u"""</label>
                        <input type="tel" name="phone" class="form-control"/>
                    </div>
                    <div class="clearfix"/>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="street2">""" + _("Street") + u"""</label>
                        <input type="text" name="street2" class="form-control"/>
                    </div>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="city">""" + _("City") + u"""</label>
                        <input type="text" name="city" class="form-control"/>
                    </div>
                    <div class="clearfix"/>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="zip" style="font-weight: normal">""" \
                            + _("Zip / Postal Code") \
                            + u"""</label>
                        <input type="text" name="zip" class="form-control"/>
                    </div>
                    <div class="clearfix"/>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="country_id">""" + _("Country") + u"""</label>
                        <select name="country_id" class="form-control">
                            <option value="">""" + _("Country...") + u"""</option>
                            ==CL_ADD_COUNTRY_OPTIONS==
                        </select>
                    </div>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="state_id" style="font-weight: normal">""" \
                            + _("State / Province") \
                            + u"""</label>
                        <select name="state_id" class="form-control">
                            <option value="">""" + _("Select...") + u"""</option>
                            ==CL_ADD_STATE_OPTIONS==
                        </select>
                    </div>
                </fieldset>


                <div class="CL_Step CL_Step1 clearfix">
                    <a class="btn pull-right mb32 a-next">""" + _("Next") \
            + u""" <span class="fa fa-long-arrow-right"/></a>
                </div>

                <div class="CL_Step CL_Step2 clearfix">
                    <a class="btn pull-left mb32 a-prev">""" + _("Previous") \
            + u""" <span class="fa fa-long-arrow-left"/></a>
                    <a class="btn pull-right mb32 a-submit">""" + _("Submit") + u""" <span class="fa"/></a>
                </div>
            </form>
        </body>
        </html>"""
