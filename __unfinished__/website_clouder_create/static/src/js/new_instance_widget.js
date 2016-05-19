/**
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
**/

openerp.oewebclcreate = function(instance, local) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    local.NewInstance = instance.Widget.extend({
        start: function() {
            var model = new instance.web.Model("clouder.web.helper");

            model.call("application_form_values", {context: new instance.web.CompoundContext()}).then(function(result) {
                this.$el.append(QWeb.render("website_clouder_create.create_app_form"));
            });
        },
    });

    instance.web.client_actions.add(
        'website_clouder_create.new_instance', 'instance.oewebclcreate.NewInstance');
}
