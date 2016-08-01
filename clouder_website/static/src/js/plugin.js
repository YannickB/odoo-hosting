Clouder.run = function($){
    Clouder.$ = $;
    Clouder.$plugin = Clouder.$('#ClouderPlugin');
    Clouder.login_validated = false;
    Clouder.clws_id = false;
    Clouder.clean = [];

    Clouder.$plugin.css('background', 'none');
    Clouder.$plugin.find('.CL_final_thanks').hide();
    Clouder.$plugin.find('.CL_final_error').hide();
    Clouder.$plugin.find('.CL_Loading').hide();
    
    Clouder.$plugin.find('#ClouderForm').each(function(){
        $clouder_form = $(this);

        // Hide hint
        $clouder_form.find('.CL_hint').hide();
        // Hide environment_id itself
        $clouder_form.find('select[name="environment_id"]').parent().hide();
        // Hide base and container specific forms until application_id is selected
        $clouder_form.find('.CL_container_form').hide();
        $clouder_form.find('.CL_base_form').hide();

        // Show step 1 by default
        Clouder.showStep(1);

        // Fill form data with already known variables
        $clouder_form.attr('action', Clouder.pluginPath + 'clouder_form/submit_form');
        $clouder_form.find('input[name="clouder_partner_id"]').val(Clouder.params['partner_id']);
        $clouder_form.find('input[name="db"]').val(Clouder.params['db']);
        $clouder_form.find('input[name="lang"]').val(Clouder.params['lang']);

        // Controls the state of env_prefix input depending on env_id
        $clouder_form.on('change', "select[name='environment_id']", function(){
            var $env_id = $clouder_form.find('select[name="environment_id"]');
            var $env_prefix = $clouder_form.find('input[name="environment_prefix"]');
            if (Clouder.login_validated && $env_id.val()){
                $env_prefix.attr('readonly', true);
                $env_prefix.attr('disabled', true);
                $env_prefix.val('');

            }
            else {
                $env_prefix.attr('readonly', false);
                $env_prefix.attr('disabled', false);
            }
        });
        $clouder_form.find('select[name="environment_id"]').change();

        // Controls the appearance of env/title inputs depending on application_id
        $clouder_form.on('change', "select[name='application_id']", function(){
            var $app_id = $clouder_form.find("select[name='application_id']");
            var $container_div = $clouder_form.find('.CL_container_form');
            var $base_div = $clouder_form.find('.CL_base_form');
            if ($app_id.find('option:selected').attr('inst_type')==='container'){
                $container_div.show();
                $base_div.hide();
            }
            else if ($app_id.find('option:selected').attr('inst_type')==='base'){
                $container_div.hide();
                $base_div.show();
            }
            else {
                $container_div.hide();
                $base_div.hide();
            }
        });
        $clouder_form.find('select[name="application_id"]').change();

        // Controls the hidden state of the password input depending on email
        $clouder_form.on('change', "input[name='email']", function(){
            // Invalidate login
            Clouder.login_validated = false;
            $clouder_form.find('select[name="environment_id"]').parent().hide();

            var $email = $clouder_form.find("input[name='email']");
            var $passwd = $clouder_form.find("input[name='password']");

            Clouder.user_login($email, $passwd, function(result){
                if (result.response != undefined){
                    if (result.response){
                        $passwd.parent().addClass('js_required');
                        $passwd.parent().show();
                    }
                    else {
                        $passwd.parent().removeClass('js_required');
                        $passwd.parent().hide();
                    }
                }
                else if (result.error != undefined) {
                    $form.hide();
                    $error = Clouder.$plugin.find('.CL_final_error');
                    $error.find('.CL_Error_msg').html(result.error);
                    $error.show();
                }
            });
        });
        $clouder_form.find("input[name='email']").change();

        // Launch login if password is changed
        $clouder_form.on('change', 'input[name="password"]', function(){
            // Invalidate login
            Clouder.login_validated = false;

            // Hide and empty env selection
            $clouder_form.find('select[name="environment_id"]').parent().hide();
            $clouder_form.find('select[name="environment_id"]').find('option:gt(0)').remove();

            var $email = $clouder_form.find("input[name='email']");
            var $passwd = $clouder_form.find("input[name='password']");

            if ($passwd.parent().hasClass('js_required') && $passwd.val()){
                Clouder.user_login($email, $passwd, function(result){
                    var $hint = Clouder.$plugin.find('.CL_hint');
                    if (result.response != undefined){
                        if (result.response){
                            $passwd.parent().removeClass('has-error');
                            $hint.hide();
                            Clouder.login_validated = true;
                            $clouder_form.find('select[name="environment_id"]').parent().show();
                        }
                        else {
                            $passwd.parent().addClass('has-error');
                            $hint.html(Clouder.getHintMsg("CL_HINT_PASSWORD"));
                            $hint.show();
                        }
                    }
                    else if (result.error != undefined) {
                        $form.hide();
                        $error = Clouder.$plugin.find('.CL_final_error');
                        $error.find('.CL_Error_msg').html(result.error);
                        $error.show();
                    }
                });
            }
        });

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
            Clouder.error_step(1);
        });

        $clouder_form.find('.a-prev').off('click').on('click', function () {
            Clouder.showStep(1);
        });
        $clouder_form.find('.a-submit').off('click').on('click', function () {
            Clouder.error_step(2);
        });
        Clouder.$plugin.find('.a-retry').off('click').on('click', function(){
            Clouder.$plugin.find('.CL_final_error').hide();
            Clouder.loading(true, $clouder_form);
            Clouder.showStep(1);
            Clouder.loading(false, $clouder_form);
        });

        // Resize and handle divs
        $clouder_form.find('fieldset').each(function(){
            var col = 0;
            $(this).find('div').each(function(){
                if ($(this).hasClass('clearfix')){
                    col = 0;
                }
                else if ($(this).hasClass('form-group')){
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

Clouder.parse_check = function(data){
    if(data.next_step_validated){
        Clouder.showStep(2);
    }
    else {
        // Display hint returned by server
        $hint = Clouder.$plugin.find('.CL_hint');
        $hint.html(data.message);
        $hint.show();

        // Removing processed variables
        delete data.message;
        delete data.next_step_validated;

        // Adding errors to elements
        for (elt in data){
            Clouder.$plugin.find("[name='"+elt+"']").parent().addClass("has-error");
        }
    }
};

Clouder.check_instance_data = function(){
    $form = Clouder.$plugin.find('#ClouderForm');
    Clouder.loading(true, $form);
    inst_type = $form.find('select[name="application_id"]').find('option:selected').attr('inst_type');
    ajax_data = {
        'inst_type': inst_type,
        'suffix': $form.find('input[name="suffix"]').val(),
        'environment_id': $form.find('select[name="environment_id"]').find('option:selected').val(),
        'environment_prefix': $form.find('input[name="environment_prefix"]').val(),
        'domain_id': $form.find('select[name="domain_id"]').find('option:selected').val(),
        'prefix': $form.find('input[name="prefix"]').val(),
    }
    Clouder.$.ajax({
        url: Clouder.pluginPath + 'clouder_form/check_data',
        data: ajax_data,
        method: 'POST',
        cache: false,
        dataType: 'html',
        success: function(data) {
            data = JSON.parse(data);
            if (data.error != undefined){
                $error = Clouder.$plugin.find('.CL_final_error');
                $error.find('.CL_Error_msg').text(data.error);

                Clouder.loading(false, $form);
                $form.hide();

                $error.show();
            }
            else if (data.html != undefined){
                Clouder.parse_check(data);
                Clouder.loading(false, $form);
            }
            else {
                Clouder.loading(false, $form);
                $form.hide();
                $error = Clouder.$plugin.find('.CL_final_error');
                $error.find('.CL_Error_msg').html(Clouder.getErrorMsg('CL_ERR_SERV_RESP'));
                $error.show();
            }
        },
        error: function(jq, txt, err) {
            Clouder.loading(false, $form);
            $form.hide();
            $error = Clouder.$plugin.find('.CL_final_error');
            $error.find('.CL_Error_msg').html(Clouder.getErrorMsg('CL_ERR_CHECK_INST'));
            $error.show();
        }
    });
};

Clouder.readresponse = function(data, cleanup=true){
    if (cleanup){
        // Clean old dynamically added divs
        for (div in Clouder.clean) {
            Clouder.$plugin.find(Clouder.clean[i]).remove();
        }
        Clouder.clean = [];
    }

    Clouder.$plugin.append('<div id="'+data.div_id+'"></div>');
    $new_div = Clouder.$plugin.find('#'+data.div_id);

    // Push new div for future cleanups
    Clouder.clean.push('#'+data.div_id);

    $new_div.html(data.html);
    for (i in data.js){
        Clouder.getScript(Clouder.pluginPath + data.js[i], function(){});
    }
    $new_div.show();
};

Clouder.loading = function(state, $selector){
    var $loading = Clouder.$plugin.find('.CL_Loading');
    if (state){
        $loading.css('background', 'black url('+Clouder.img_loading+') no-repeat center center');
        $loading.css('height', $form.height());
        $loading.css('width', $form.width());
        $selector.hide();
        Clouder.$plugin.find('.CL_hint').hide();
        $loading.show();
    }
    else {
        $loading.css('background', '');
        $loading.hide();
        $selector.show();
    }
};

Clouder.getErrorMsg = function(err_id){
    return Clouder.$plugin.find('#CL_ERROR_MESSAGES>#'+err_id).html();
}
Clouder.getHintMsg = function(hint_id){
    return Clouder.$plugin.find('#CL_HINT_MESSAGES>#'+hint_id).html();
}

Clouder.submit_override = function(){
    var $form = Clouder.$plugin.find('#ClouderForm');

    Clouder.loading(true, $form);

    // Empty env values depending on application type
    $app_id = $form.find('select[name="application_id"]');
    if ($app_id.find('option:selected').attr('inst_type')!=='container'){
        $form.find('select[name="suffix"]').val('');
        $form.find('select[name="environment_id"]').val('');
        $form.find('input[name="environment_prefix"]').val('');
    }
    else if ($app_id.find('option:selected').attr('inst_type')!=='base'){
        $form.find('select[name="prefix"]').val('');
        $form.find('select[name="title"]').val('');
        $form.find('input[name="domain_id"]').val('');
    }

    Clouder.$.ajax({
        url: $form.attr('action'),
        data: $form.serialize(),
        method: 'POST',
        cache: false,
        dataType: 'html',
        success: function(data) {
            data = JSON.parse(data);
            if (data.error != undefined){
                Clouder.loading(false, $form);
                $form.hide();
                $error = Clouder.$plugin.find('.CL_final_error');
                $error.find('.CL_Error_msg').html(data.error);
                $error.show();
            }
            else if (data.html != undefined){
                Clouder.readresponse(data);
                Clouder.clws_id = data.clws_id;
                Clouder.loading(false, $form);
                $form.hide();
            }
            else {
                Clouder.loading(false, $form);
                $form.hide();
                $error = Clouder.$plugin.find('.CL_final_error');
                $error.find('.CL_Error_msg').html(Clouder.getErrorMsg('CL_ERR_SERV_RESP'));
                $error.show();
            }
        },
        error: function(jq, txt, err) {
            Clouder.loading(false, $form);
            $form.hide();
            $error = Clouder.$plugin.find('.CL_final_error');
            $error.find('.CL_Error_msg').html(Clouder.getErrorMsg('CL_ERR_SUB_FORM'));
            $error.show();
        }
    });
};

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

Clouder.phone_re = /^((\+[1-9]{1,4}[ \-]*)|(\([0-9]{2,3}\)[ \-]*)|([0-9]{2,4})[ \-]*)*?[0-9]{3,4}?[ \-]*[0-9]{3,4}?$/;
Clouder.email_re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
Clouder.cont_suff_re = /^[\w\d-]*$/;
Clouder.base_pref_re = /^[\w\d.-]*$/;
Clouder.env_pref_re = /^[\w]*$/;
Clouder.error_regexp = function($elt, re, err_msg){
    var elt_val = $elt.val();
    var err_class = "has-error";
    var $hint = Clouder.$plugin.find('.CL_hint');
    if (elt_val == '' || !re.test(elt_val))
    {
        $elt.parent().addClass(err_class);
        $hint.html(err_msg);
        return true;
    }
    $elt.parent().removeClass(err_class);
    return false;
}

Clouder.error_step = function(step){
    var has_error = false;
    var $hint = Clouder.$plugin.find('.CL_hint');
    $hint.html('');
    $hint.hide();

    if (step == 1){
        $app_select = Clouder.$plugin.find('select[name="application_id"]');
        $password_select = Clouder.$plugin.find('input[name="password"]');
        $email_select = Clouder.$plugin.find('input[name="email"]');
        
        has_error = Clouder.add_error_to_elt($app_select) || has_error;
        has_error = Clouder.error_regexp(
            $email_select,
            Clouder.email_re,
            Clouder.getHintMsg("CL_HINT_EMAIL"),
        ) || has_error;

        if ($app_select.find('option:selected').attr('inst_type')==='container'){
            $suffix = Clouder.$plugin.find('input[name="suffix"]');
            $env_prefix = Clouder.$plugin.find('input[name="environment_prefix"]');
            $env_id = Clouder.$plugin.find('select[name="environment_id"]');

            has_error = Clouder.error_regexp(
                $suffix,
                Clouder.cont_suff_re,
                Clouder.getHintMsg("CL_HINT_SUFFIX"),
            ) || has_error;

            if (!$env_id.val() && !$env_prefix.val()){
                has_error = true;
                $env_id.parent().addClass('has-error');
                $env_prefix.parent().addClass('has-error');
            }
            else if (!$env_id.val()) {
                // Checking environment_prefix with regexp
                has_error = Clouder.error_regexp(
                    $env_prefix,
                    Clouder.env_pref_re,
                    Clouder.getHintMsg("CL_HINT_ENV_PREFIX"),
                ) || has_error;
            }
            else {
                $env_id.parent().removeClass('has-error');
                $env_prefix.parent().removeClass('has-error');
            }
        }
        else if ($app_select.find('option:selected').attr('inst_type')==='base'){
            $domain_select = Clouder.$plugin.find('select[name="domain_id"]');
            $prefix_input = Clouder.$plugin.find('input[name="prefix"]');
            $title_input = Clouder.$plugin.find('input[name="title"]');

            has_error = Clouder.error_regexp(
                $prefix_input,
                Clouder.base_pref_re,
                Clouder.getHintMsg("CL_HINT_PREFIX"),
            ) || has_error;

            has_error = Clouder.add_error_to_elt($title_input) || has_error;
            has_error = Clouder.add_error_to_elt($domain_select) || has_error;
        }

        if (has_error){
            if (!$hint.html()){
                $hint.html(Clouder.getHintMsg("CL_HINT_GENERAL"));
            }
            $hint.show();
        }

        if ($password_select.parent().hasClass('js_required')){
            has_error = Clouder.add_error_to_elt($password_select) || has_error;
            has_error = !Clouder.login_validated || has_error;
            if (!Clouder.login_validated){
                $hint.html(Clouder.getHintMsg("CL_HINT_PASSWORD"));
                $hint.show();
            }
        }

        // If there's no error after all that, we can check the data with the server
        if (!has_error){
            Clouder.check_instance_data();
        }
    }
    else if (step == 2){
        $name_select = Clouder.$plugin.find('input[name="name"]');
        $phone_select = Clouder.$plugin.find('input[name="phone"]');
        $street2_select = Clouder.$plugin.find('input[name="street2"]');
        $city_select = Clouder.$plugin.find('input[name="city"]');
        $country_select = Clouder.$plugin.find('select[name="country_id"]');

        has_error = Clouder.add_error_to_elt($name_select) || has_error;
        has_error = Clouder.error_regexp(
            $phone_select,
            Clouder.phone_re,
            Clouder.getHintMsg("CL_HINT_PHONE"),
        ) || has_error;
        has_error = Clouder.add_error_to_elt($street2_select) || has_error;
        has_error = Clouder.add_error_to_elt($city_select) || has_error;
        has_error = Clouder.add_error_to_elt($country_select) || has_error;

        if (!has_error){
            Clouder.submit_override();
        }
        else {
            if (!$hint.html()){
                $hint.html(Clouder.getHintMsg("CL_HINT_GENERAL"));
            }
            $hint.show();
        }
    }

    if (!has_error){
        $hint.hide();
    }
};

/*
    Sets the env_id options for the given registered user
*/
Clouder.get_env = function($login, $password, when_callback){
    // Put the form in loading mode
    $form = Clouder.$plugin.find('#ClouderForm');
    Clouder.loading(true, $form);

    // Declare vars
    var result = {'res': false, 'error': false};

    function ajax_get_env(){
        return Clouder.$.ajax({
            url: Clouder.pluginPath + 'clouder_form/get_env',
            data: {
                'login': $login.val(),
                'password': $password.val(),
                'lang': Clouder.params['lang']
            },
            method:'POST',
            cache: false,
            dataType: 'html',
            success: function(data) {
                result = JSON.parse(data);
            },
            error: function(jq, txt, err) {
                result = {'error': Clouder.getErrorMsg('CL_ERR_GET_ENV')};
            }
        });
    };

    if ($login.val()){
        Clouder.$.when(ajax_get_env()).always(function(useless){
            when_callback(result);
            Clouder.loading(false, $form);
        });
    }
    else {
        // Hide password and empty value
        $password.parent().removeClass('js_required');
        $password.val('');
        $password.parent().hide();
        Clouder.loading(false, $form);
    }

}

/*
    If login is passed: returns true if the login exists
    If login and password are passed: return true if you can authenticate on the DB with these
*/
Clouder.user_login = function($login, $password, when_callback){
    // Put the form in loading mode
    $form = Clouder.$plugin.find('#ClouderForm');
    Clouder.loading(true, $form);

    // Declare vars
    var result = {'res': false, 'error': false};

    function axaj_login(){
        return Clouder.$.ajax({
            url: Clouder.pluginPath + 'clouder_form/form_login',
            data: {'login': $login.val(), 'password': $password.val()},
            method:'POST',
            cache: false,
            dataType: 'html',
            success: function(data) {
                result = JSON.parse(data);
            },
            error: function(jq, txt, err) {
                result = {'error': Clouder.getErrorMsg('CL_ERR_LOGIN')};
            }
        });
    };

    if ($login.val()){
        Clouder.$.when(axaj_login()).always(function(useless){
            when_callback(result);
            Clouder.loading(false, $form);
            // Successfull login with password provided
            if (result.response && $password.val()){
                // Read and apply partner info

                for(attr_name in result.partner_info){
                    // Select attributes
                    if(attr_name.match(/_id$/)){
                        $select = Clouder.$plugin.find('select[name="'+attr_name+'"]');
                        $select.find('option:selected').removeAttr("selected");
                        $select.val(result.partner_info[attr_name]);
                    }
                    // Other attributes
                    else {
                        $field = Clouder.$plugin.find('input[name="'+attr_name+'"]');
                        $field.val(result.partner_info[attr_name]);
                    }

                }

                // Get environment info
                Clouder.get_env($login, $password, function(data){
                    var first = true;
                    $hint = Clouder.$plugin.find('.CL_hint');
                    if (data.result != undefined){
                        for(env_id in data.result){
                            $env_select = Clouder.$plugin.find('select[name="environment_id"]');

                            // Add option for each env
                            $env_select.append('<option value="'+env_id+'">'+data.res[env_id]['name']+'</option>');

                            // Select the first added env
                            if (first){
                                first = false;
                                $env_select.val(env_id);
                            }
                            $env_select.parent().show();
                            $env_select.change();
                        }
                    }
                    else {
                        $form.hide();
                        $error = Clouder.$plugin.find('.CL_final_error');
                        $error.find('.CL_Error_msg').html(data.error);
                        $error.show();
                    }
                });
            }
        });
    }
    else {
        // Hide password and empty value
        $password.parent().removeClass('js_required');
        $password.val('');
        $password.parent().hide();
        Clouder.loading(false, $form);
    }

}

// Displays the right elements, corresponding to the current step. Hides the others.
Clouder.showStep = function(step){
    Clouder.$plugin.find('.CL_Step').hide();
    Clouder.$plugin.find('.CL_Step'+step).show();
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

Clouder.img_loading = Clouder.pluginPath + "clouder_website/static/src/img/loading32x32.gif"

Clouder.loadPhp = function ($) {
    $('#ClouderPlugin').css('min-height', '52px');
    $.ajax({
        url: Clouder.pluginPath + 'clouder_form/request_form',
        data: Clouder.params,
        method:'POST',
        dataType: 'html',
        cache: false,
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
