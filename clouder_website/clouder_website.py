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

from openerp import models, fields, api, http, _
from openerp.exceptions import except_orm
from xmlrpclib import ServerProxy
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
        application = self.browse(data['application_id'])
        partner = data['request_partner']

        if not data['env_id']:
            env_obj = self.env['clouder.environment']
            env_id = env_obj.search([('partner_id', '=', partner.id)])
            if env_id:
                data['env_id'] = env_id[0].id
            else:
                data['env_id'] = env_obj.create({
                    'name': partner.name,
                    'partner_id': partner.id,
                    'prefix': data['env_prefix']  # Can be False
                }).id

        if application.web_create_type == 'container':
            return self.env['clouder.container'].create({
                'environment_id': data['env_id'],
                'suffix': data['prefix'],
                'application_id': application.id
            })
        elif application.web_create_type == 'base':
            return self.env['clouder.base'].create({
                'name': data['prefix'],
                'domain_id': data['domain_id'],
                'environment_id': data['env_id'],
                'title': data['title'],
                'application_id': application.id,
                'poweruser_name': partner.email,
                'poweruser_email': partner.email,
                'lang': 'lang' in self.env.context and self.env.context['lang'] or 'en_US',
                'ssl_only': True,
                'autosave': True,
            })

        return False


class ClouderWebSession(models.Model):
    """
    A class to store session info from the external web form
    """
    _name = 'clouder.web.session'

    def _get_name(self):
        """
        Computes a name for a clouder web session
        """
        return self.partner_id.name.replace(' ', '_') + fields.Date.today()

    name = fields.Char("Name", compute='_get_name', required=False)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    clouder_partner_id = fields.Many2one('res.partner', 'Sales Partner', required=True)
    application_id = fields.Many2one('clouder.application', 'Application', required=True)
    domain_id = fields.Many2one('clouder.domain', 'Domain', required=True)
    prefix = fields.Char('Prefix', required=True)
    title = fields.Char('Title')
    environment_id = fields.Many2one('clouder.environment', 'Environment')
    environment_prefix = fields.Char('Environment prefix')

    @api.one
    @api.constrains('application_id', 'title', 'environment_id', 'environment_prefix')
    def _check_complex_requirements(self):
        """
        Checks fields requirements that are dependant on others
        """
        if self.application_id.web_create_type == "base":
            if not self.title:
                raise except_orm(
                    _('Data error!'),
                    _("You need to specify a title when applying for a base"))
        elif self.application_id.web_create_type == "container":
            if not (self.environment_id or self.environment_prefix):
                raise except_orm(
                    _('Data error!'),
                    _("You need to specify an existing or new environment when applying for a container"))


class ClouderWebHelper(models.Model):
    """
    A class made to be called by widgets and webpages alike
    """
    _name = 'clouder.web.helper'

    @api.model
    def set_invoicing(self):
        """
        This function should be overriden by clouder payment modules
        Returns the amount to invoice
        """
        return 0

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
            except ValueError:
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
    def get_env_ids(self, uid):
        """
        Returns the existing environment ids for the given uid
        """
        env_orm = self.env['clouder.environment'].sudo()
        user_orm = self.env['res.users'].sudo()

        user = user_orm.browse([uid])[0]
        env_ids = env_orm.search([('partner_id', '=', user.partner_id.id)])

        res = {}
        for env in env_ids:
            res[str(env.id)] = {
                'name': env.name
            }

        return res

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
        html = self.get_form_template()

        # Load data from odoo
        data = self.application_form_values()

        # Apply data to template
        # Applications
        options = u""
        for app in data['applications']:
            options += u"""<option inst_type="{a.web_create_type}" value="{a.id}">{a.name}</option>""".format(a=app)
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
    def check_login_exists(self, login):
        orm_user = self.env['res.users'].sudo()
        return bool(orm_user.search([('login', '=', login)]))

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
            'clouder_partner_id',
            'title'
        ]
        instance_optional_fields = [
            'env_id',
            'env_prefix'
        ]
        other_fields = [
            'password'
        ]

        # Checking data
        partner_data = {}
        for mandat in partner_mandatory_fields:
            if mandat not in post_data or not post_data[mandat]:
                return {"code": 1, 'msg': 'Missing field "{0}"'.format(mandat)}
            partner_data[mandat] = post_data[mandat]
        for opt in partner_optionnal_fields:
            if opt in post_data:
                partner_data[opt] = post_data[opt]

        instance_data = {}
        for mandat in instance_mandatory_fields:
            if mandat not in post_data or not post_data[mandat]:
                return {"code": 1, 'msg': 'Missing field "{0}"'.format(mandat)}
            instance_data[mandat] = post_data[mandat]

        for opt in instance_optional_fields:
            if opt in post_data:
                instance_data[opt] = post_data[opt]
            else:
                instance_data[opt] = False

        other_data = {}
        for opt in other_fields:
            if opt in post_data:
                other_data[opt] = post_data[opt]
            else:
                other_data[opt] = False

        # All data retrieved
        orm_partner = self.env['res.partner'].sudo()
        orm_user = self.env['res.users'].sudo()

        # If the user exists, try to login and update partner
        if self.check_login_exists(partner_data['email']):
            server = ServerProxy('http://localhost:8069/xmlrpc/common')
            user_id = server.login(self.env.cr.dbname, partner_data['email'], other_data['password'])
            if not user_id:
                return {"code": 2, 'msg': 'Incorrect user/password'}
            user = orm_user.browse([user_id])[0]

            if user.partner_id:
                user.partner_id.write(partner_data)
                instance_data['request_partner'] = user.partner_id
            else:
                instance_data['request_partner'] = orm_partner.create(partner_data)
                user.sudo().write({'partner_id': instance_data['request_partner'].id})

        # If the user doesn't exist, create a new partner and user
        else:
            instance_data['request_partner'] = orm_partner.create(partner_data)
            user = orm_user.create({
                'login': partner_data['email'],
                'partner_id': instance_data['request_partner'].id
            })

            # Add user to Clouder user group
            self.env.ref('clouder.group_clouder_user').sudo().write({
                'users': [(4, user.id)]
            })

        # Parsing instance data
        instance_data['clouder_partner_id'] = int(instance_data['clouder_partner_id'])
        instance_data['application_id'] = int(instance_data['application_id'])
        instance_data['domain_id'] = int(instance_data['domain_id'])

        # Creating session using information
        orm_cws = self.env['clouder.web.session'].sudo()
        session_id = orm_cws.create(instance_data)

        return {
            'code': 0,
            'msg': 'Session created',
            'session_id': session_id,
            'payment': False
        }

    def submit_payment(self, clouder_web_session_id, vendor_response):
        """
        Should be overriden by clouder payment modules
        Checks that the vendor response is OK and creates the instance using session info
        """

        # In this default version, payment isn't even checked
        orm_cws = self.env['clouder.web.session'].sudo()
        session_info = orm_cws.browse([clouder_web_session_id])[0]

        data = {
            'clouder_partner_id': session_info.clouder_partner_id.id,
            'application_id': session_info.application_id.id,
            'domain_id': session_info.domain_id.id,
            'request_partner': session_info.partner_id.id,
            'prefix': session_info.prefix,
            'title': session_info.title,
            'env_id': session_info.environment_id.id,
            'env_prefix': session_info.environment_prefix
        }

        # Calling instance creation function
        orm_app = self.env['clouder.application'].sudo()
        orm_app.create_instance_from_request(data)

        return {'code': 0, 'msg': 'Instance creation launched'}

    def get_form_template(self):
        """
        Returns the HTML form template with odoo-translated strings
        """
        # Return the template
        return \
            u"""<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
        <html>
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        <title>""" + _("Clouder instance request form") + u"""</title>

        <style type="text/css">
        /* Elements */
        #ClouderPlugin a
        {
            color: #428bca;
            text-decoration: none;
            background: transparent;
        }
        #ClouderPlugin a:active, a:hover
        {
            outline: 0;
        }
        #ClouderPlugin a:hover, a:focus
        {
            color: #2a6496;
            text-decoration: underline;
        }
        #ClouderPlugin a:focus
        {
            outline: 5px auto -webkit-focus-ring-color;
            outline: thin dotted;
            outline-offset: -2px;
        }
        #ClouderPlugin input
        {
            line-height: normal;
        }
        #ClouderPlugin input[disabled]
        {
            cursor: default;
        }
        #ClouderPlugin select
        {
            text-transform: none;
        }
        #ClouderPlugin input, #ClouderPlugin select
        {
            font-family: inherit;
            font-size: inherit;
            line-height: inherit;
            color: inherit;
            font: inherit;
            margin: 0;
        }
        #ClouderPlugin label
        {
            display: inline-block;
            font-weight: bold;
            margin-bottom: 5px;
            max-width: 100%;
        }

        /* Classes */
        #ClouderPlugin .CL_hint
        {
            color: red;
            text-align: center;
        }
        #ClouderPlugin .CL_Loading
        {
            position:relative;

            /* IE 8 */
            -ms-filter: "progid:DXImageTransform.Microsoft.Alpha(Opacity=50)";
            /* IE 5-7 */
            filter: alpha(opacity=50);
            /* Netscape */
            -moz-opacity: 0.5;
            /* Safari 1.x */
            -khtml-opacity: 0.5;
            /* Good browsers */
            opacity: 0.5;
        }
        #ClouderPlugin .CF_Title
        {
            font-size: 25px;
            text-align: center;
            margin: .67em 0;
            color: inherit;
            font-family: inherit;
            font-weight: 500;
            line-height: 1.1;
            margin-bottom: 10px;
            margin-top: 20px;
        }
        #ClouderPlugin .mb32
        {
            margin-bottom: 32px !important;
        }
        #ClouderPlugin .pull-right
        {
            float: right !important;
            position: relative !important;
            right: 10px;
        }
        #ClouderPlugin .pull-left
        {
            float: left !important;
            position: relative !important;
            left: 10px;
        }
        #ClouderPlugin .btn:hover, #ClouderPlugin .btn:focus, #ClouderPlugin .btn:active,""" \
        + u"""#ClouderPlugin .btn.active
        {
            background-color: #e6e6e6;
            border-color: #adadad;
            color: #333;
            background-color: #3071a9;
            border-color: #285e8e;
            color: #fff;
        }
        #ClouderPlugin .btn:active, #ClouderPlugin .btn.active
        {
            background-image: none;
        }
        #ClouderPlugin .btn
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
        #ClouderPlugin .btn:focus, #ClouderPlugin .btn:active:focus, #ClouderPlugin .btn.active:focus
        {
            outline: 5px auto -webkit-focus-ring-color;
            outline: thin dotted;
            outline-offset: -2px;
        }
        #ClouderPlugin .btn:hover, #ClouderPlugin .btn:focus
        {
            color: #333;
            text-decoration: none;
        }
        #ClouderPlugin .btn:active, #ClouderPlugin .btn.active
        {
            background-image: none;
            box-shadow: inset 0 3px 5px rgba(0, 0, 0, .125);
            outline: 0;
            webkit-box-shadow: inset 0 3px 5px rgba(0, 0, 0, .125);
        }
        #ClouderPlugin .form-control
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
        #ClouderPlugin input[class="form-control"]
        {
            height: 20px;
        }
        #ClouderPlugin select[class="form-control"]
        {
            width: 118%;
        }
        #ClouderPlugin .form-control:focus
        {
            border-color: #66afe9;
            box-shadow: inset 0 1px 1px rgba(0,0,0,.075), 0 0 8px rgba(102, 175, 233, .6);
            outline: 0;
            webkit-box-shadow: inset 0 1px 1px rgba(0,0,0,.075), 0 0 8px rgba(102, 175, 233, .6);
        }
        #ClouderPlugin .form-control::-moz-placeholder
        {
            color: #777;
            opacity: 1;
        }
        #ClouderPlugin .form-control:-ms-input-placeholder
        {
            color: #777;
        }
        #ClouderPlugin .form-control::-webkit-input-placeholder
        {
            color: #777;
        }
        #ClouderPlugin .form-control[disabled], .form-control[readonly], fieldset[disabled] .form-control
        {
            background-color: #eee;
            cursor: not-allowed;
            opacity: 1;
        }
        #ClouderPlugin .has-error .form-control
        {
            border-color: #a94442;
            box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075);
            webkit-box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075);
        }
        #ClouderPlugin .has-error .form-control:focus
        {
            border-color: #843534;
            box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075), 0 0 6px #ce8483;
            webkit-box-shadow: inset 0 1px 1px rgba(0, 0, 0, .075), 0 0 6px #ce8483;
        }
        #ClouderPlugin .has-error .control-label
        {
            color: #a94442;
        }
        #ClouderPlugin .col-lg-6
        {
            min-height: 1px;
            padding-left: 0px;
            padding-right: 25px;
            position: relative;
        }
        #ClouderPlugin .clearfix:after, #ClouderPlugin .form-group:after
        {
            clear: both;
        }
        #ClouderPlugin .clearfix:before, #ClouderPlugin .clearfix:after, #ClouderPlugin .form-group:before,""" \
        + u"""#ClouderPlugin .form-group:after
        {
            content: " ";
            display: table;
        }
        #ClouderPlugin .clearfix:before, #ClouderPlugin .clearfix:after
        {
            content: " ";
            display: table;
        }
        #ClouderPlugin .form-group
        {
            margin-bottom: 15px;
            width: 40%;
        }
        #ClouderPlugin .fa
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
            <p class="CF_Title">""" + _("Request a Clouder Instance") + u"""</p>
            <div class="CL_Loading"/>
            <form id="ClouderForm" method="POST" action="">
                <input type="hidden" name="clouder_partner_id" value=""/>
                <input type="hidden" name="lang" value=""/>
                <input type="hidden" name="db" value=""/>


                <fieldset class="CL_Step CL_Step1">
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="application_id">""" + _("Application") + u"""</label>
                        <select name="application_id" class="form-control">
                            <option value="">""" + _("Application...") + u"""</option>
                            ==CL_ADD_APPLICATION_OPTIONS==
                        </select>
                    </div>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="title">""" + _("Instance title") + u"""</label>
                        <input type="text" name="title" class="form-control"/>
                    </div>
                    <div class="clearfix"/>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="prefix">""" + _("Subdomain") + u"""</label>
                        <input type="text" name="prefix" class="form-control"/>
                    </div>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="domain_id">""" + _("Domain Name") + u"""</label>
                        <select name="domain_id" class="form-control">
                            <option value="">""" + _("Domain...") + u"""</option>
                            ==CL_ADD_DOMAIN_OPTIONS==
                        </select>
                    </div>
                    <div class="clearfix"/>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="email">""" + _("Email") + u"""</label>
                        <input type="email" name="email" class="form-control"/>
                    </div>
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="password">""" + _("Password") + u"""</label>
                        <input type="password" name="password" class="form-control"/>
                    </div>
                    <div class="clearfix"/>
                    <div id="CL_env_form">
                        <div class="form-group col-lg-6">
                            <label class="control-label" for="env_prefix">""" + _("New environment name") + u"""</label>
                            <input type="text" name="env_prefix" class="form-control"/>
                        </div>
                        <div class="form-group col-lg-6">
                            <label class="control-label" for="env_id">
                                """ + _("... or use an existing one") + u"""</label>
                            <select name="env_id" class="form-control">
                                <option value="">""" + _("<= Use new name") + u"""</option>
                            </select>
                        </div>
                    </div>
                </fieldset>

                <fieldset class="CL_Step CL_Step2">
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="name">""" + _("Your Name") + u"""</label>
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
                    <div class="form-group col-lg-6">
                        <label class="control-label" for="phone">""" + _("Phone") + u"""</label>
                        <input type="tel" name="phone" class="form-control"/>
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

                <div class="CL_hint">
                </div>

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
            <p class="CL_final_thanks">""" + _("Your request for a Clouder instance has been sent.") + u"""<br/>""" \
            + _("Thank you for your interest in Clouder!") + u"""</p>

            <div class="CL_final_error">
                <span class="CL_Error_msg"/>
                <div class="clearfix"/>
                <a class="btn pull-left mb32 a-retry">""" + _("Retry") \
            + u""" <span class="fa fa-long-arrow-left"/></a>
            </div>
        </body>
        </html>"""
