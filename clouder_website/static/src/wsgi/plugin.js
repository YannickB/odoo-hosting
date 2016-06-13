Clouder.run = function($){
    $odoo_plugin = $('#ClouderPlugin');
    $odoo_plugin.css('background', 'none');
    $odoo_plugin.find('.CL_thanks').hide();
    
    $('#ClouderForm').each(function(){
        $clouder_form = $(this);
        // Show step 1 by default
        Clouder.showStep($clouder_form, 1);
        // Fill form data with already known variables
        $clouder_form.attr('action', Clouder.pluginPath + 'submit_form');
        $clouder_form.find('input[name="clouder_partner_id"]').val(Clouder.params['partner_id']);
        $clouder_form.find('input[name="db"]').val(Clouder.params['db']);
        $clouder_form.find('input[name="lang"]').val(Clouder.params['lang']);

        // Controls the hidden state of the state selector depending on country
        $clouder_form.on('change', "select[name='country_id']", function () {
            var $select = $clouder_form.find("select[name='state_id']");
            $select.find("option:not(:first)").hide();
            var nb = $select.find("option[country_id="+($(this).val() || 0)+"]").show().size();
            $select.parent().toggle(nb>1);
        });
        $clouder_form.find("select[name='country_id']").change();

        // Buttons handlers
        $clouder_form.find('.a-next').off('click').on('click', function () {
            if (!Clouder.error_step($clouder_form, 1)){
                Clouder.showStep($clouder_form, 2);
            }
        });

        $clouder_form.find('.a-prev').off('click').on('click', function () {
            Clouder.showStep($clouder_form, 1);
        });
        $clouder_form.find('.a-submit').off('click').on('click', function () {
            if (!Clouder.error_step($clouder_form, 2)){
                Clouder.submit_override($, $clouder_form, $odoo_plugin);
            }
        });

        // Resize and handle divs
        $clouder_form.find('fieldset').each(function(){
            var col = 0;
            $(this).find('div').each(function(){
                if ($(this).hasClass('clearfix')){
                    col = 0;
                }
                else {
                    if (col % 2 === 0){
                        $(this).css('float', 'left');
                    }
                    else{
                        $(this).css('float', 'right');
                    }
                    col = col + 1;
                }
            });
        });
    });
};

Clouder.submit_override = function($, $form, $plugin){
    $.ajax({
        url: $form.attr('action'),
        data: $form.serialize(),
        method: 'POST',
        dataType: 'html',
        success: function(msg) {
            $form.hide();
            $plugin.find('.CL_thanks').show();
        },
        error: function(jq, txt, err) {
            $plugin.html("ERROR: Could not submit form");
        }
    });
}

Clouder.add_error_to_elt = function($elt){
    var err_class = "has-error";
    if (!$elt.val())
    {
        $elt.parent().addClass(err_class);
        return true;
    }
    $elt.parent().removeClass(err_class);
    return false;
};

Clouder.error_email = function($elt){
    var email = $elt.val();
    var err_class = "has-error";
    var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    if (email == '' || !re.test(email))
    {
        $elt.parent().addClass(err_class);
        return true;
    }
    $elt.parent().removeClass(err_class);
    return false;
};

Clouder.error_step = function($current, step){
    var has_error = false;
    if (step == 1){
        $app_select = $current.find('select[name="application_id"]');
        $domain_select = $current.find('select[name="domain_id"]');
        $prefix_input = $current.find('input[name="prefix"]');
        
        has_error = Clouder.add_error_to_elt($app_select) || has_error;
        has_error = Clouder.add_error_to_elt($domain_select) || has_error;
        has_error = Clouder.add_error_to_elt($prefix_input) || has_error;
    }
    else if (step == 2){
        $name_select = $current.find('input[name="name"]');
        $phone_select = $current.find('input[name="phone"]');
        $email_select = $current.find('input[name="email"]');
        $street2_select = $current.find('input[name="street2"]');
        $city_select = $current.find('input[name="city"]');
        $country_select = $current.find('select[name="country_id"]');
        
        has_error = Clouder.add_error_to_elt($name_select) || has_error;
        has_error = Clouder.add_error_to_elt($phone_select) || has_error;
        has_error = Clouder.error_email($email_select) || has_error;
        has_error = Clouder.add_error_to_elt($street2_select) || has_error;
        has_error = Clouder.add_error_to_elt($city_select) || has_error;
        has_error = Clouder.add_error_to_elt($country_select) || has_error;
    }
    return has_error;
};

// Displays the right elements, corresponding to the current step. Hides the others.
Clouder.showStep = function($current, step){
    $current.find('.CL_Step').hide();
    $current.find('.CL_Step'+step).show();
};

// Loads JQuery plugins and sets default values
Clouder.loadJQueryPlugins = function() {
    jQuery.noConflict(); // Avoid conflicts between our JQuery and the possibly existing one
    jQuery(document).ready(function($) {
        Clouder.params.langShort = Clouder.params.lang.split('_')[0];
        // Loads the form content in the ClouderPlugin div and launches the javascript
        Clouder.loadPhp($);
    });
};

Clouder.loadPhp = function ($) {
    $('#ClouderPlugin').css('min-height', '52px');
    $.ajax({
        url: Clouder.pluginPath + 'request_form',
        data: Clouder.params,
        method:'POST',
        dataType: 'html',
        success: function(data) {
            $('#ClouderPlugin').html(data);
            Clouder.run($);
        },
        error: function(jq, txt, err) {
            $('#ClouderPlugin').html("ERROR: Could not load form")
        }
    });
};

// Loads and external javascript and launches a function if successful
Clouder.getScript = function (url, success) {
    var script = document.createElement('script');
    script.src = url;
    var head = document.getElementsByTagName('head')[0],
    done = false;

    script.onload = script.onreadystatechange = function() {
        if (!done && (!this.readyState || this.readyState == 'loaded' || this.readyState == 'complete')) {
        done = true;
            // Launch the argument-given function
            success();
            script.onload = script.onreadystatechange = null;
            head.removeChild(script);
        };
    };
    head.appendChild(script);
};

// Loads jQUeryUi if it's not done already
Clouder.getJqueryUi = function() {
    if (typeof jQuery.ui == 'undefined') {
        jQuery("head").append("<link rel='stylesheet' type='text/css' href='//ajax.googleapis.com/ajax/libs/jqueryui/1/themes/south-street/jquery-ui.min.css' />");
        Clouder.getScript('//ajax.googleapis.com/ajax/libs/jqueryui/1/jquery-ui.min.js', function() {
            Clouder.loadJQueryPlugins();
        });
    }else{
        Clouder.loadJQueryPlugins();
    }
};



// The following part launches the bootstrap sequence

// Loads jQuery if it's not loaded already
if (typeof jQuery == 'undefined') {
    Clouder.getScript('//ajax.googleapis.com/ajax/libs/jquery/1/jquery.min.js', function() {
        // Loading the rest inside the newly loaded jQuery
        Clouder.getJqueryUi();
    });
} else {
    // Loading the rest on the already loaded jQuery
    Clouder.getJqueryUi();
};