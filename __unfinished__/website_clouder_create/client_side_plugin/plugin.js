TestOdoo.pluginPath = 'http://mblaptop:8065/';

TestOdoo.run = function($){
    $('#TestOdooPlugin').css('background', 'none');
    
    $('#ClouderForm').each(function(){
        $clouder_form = $(this);
        //Show step 1 by default
        TestOdoo.showStep($clouder_form, 1);
        //Fill form data with already known variables
        $clouder_form.find('form').attr('action', TestOdoo.pluginPath + 'submit_form');
        $clouder_form.find('input[name="clouder_partner_id"]').val(TestOdoo.params['partner_id']);
        $clouder_form.find('input[name="db"]').val(TestOdoo.params['db']);

        //Controls the hidden state of the state selector depending on country
        $clouder_form.on('change', "select[name='country_id']", function () {
            var $select = $clouder_form.find("select[name='state_id']");
            $select.find("option:not(:first)").hide();
            var nb = $select.find("option[country_id="+($(this).val() || 0)+"]").show().size();
            $select.parent().toggle(nb>1);
        });
        $clouder_form.find("select[name='country_id']").change();

        //Buttons handlers
        $clouder_form.find('.a-next').off('click').on('click', function () {
            if (!TestOdoo.error_step($clouder_form, 1)){
                TestOdoo.showStep($clouder_form, 2);
            }
        });

        $clouder_form.find('.a-prev').off('click').on('click', function () {
            TestOdoo.showStep($clouder_form, 1);
        });
        $clouder_form.find('.a-submit').off('click').on('click', function () {
            if (!TestOdoo.error_step($clouder_form, 2)){
                $(this).closest('form').submit();
            }
        });

        //Resize and handle divs
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

TestOdoo.add_error_to_elt = function($elt){
    var err_class = "has-error";
    if (!$elt.val())
    {
        $elt.parent().addClass(err_class);
        return true;
    }
    $elt.parent().removeClass(err_class);
    return false;
};

TestOdoo.error_step = function($current, step){
    var has_error = false;
    if (step == 1){
        $app_select = $current.find('select[name="application_id"]');
        $domain_select = $current.find('select[name="domain_id"]');
        $prefix_input = $current.find('input[name="prefix"]');
        
        has_error = TestOdoo.add_error_to_elt($app_select) || has_error;
        has_error = TestOdoo.add_error_to_elt($domain_select) || has_error;
        has_error = TestOdoo.add_error_to_elt($prefix_input) || has_error;
    }
    else if (step == 2){
        $name_select = $current.find('input[name="name"]');
        $phone_select = $current.find('input[name="phone"]');
        $email_select = $current.find('input[name="email"]');
        $street2_select = $current.find('input[name="street2"]');
        $city_select = $current.find('input[name="city"]');
        $country_select = $current.find('select[name="country_id"]');
        
        has_error = TestOdoo.add_error_to_elt($name_select) || has_error;
        has_error = TestOdoo.add_error_to_elt($phone_select) || has_error;
        has_error = TestOdoo.add_error_to_elt($email_select) || has_error;
        has_error = TestOdoo.add_error_to_elt($street2_select) || has_error;
        has_error = TestOdoo.add_error_to_elt($city_select) || has_error;
        has_error = TestOdoo.add_error_to_elt($country_select) || has_error;
    }
    return has_error;
};

TestOdoo.showStep = function($current, step){
    // affiche les champs correspondant à la bonne étape
    $current.find('.CL_Step').hide();
    $current.find('.CL_Step'+step).show();
};

//charge les plugins jQuery et règle les valeurs par défaut
TestOdoo.loadJQueryPlugins = function() {
    jQuery.noConflict(); // évite que notre version de jQuery entre en conflit avec l'hôte
    jQuery(document).ready(function($) {
        //$('#TestOdooPlugin').css('background', 'url('+TestOdoo.loading+') no-repeat center bottom');
        
        TestOdoo.params.langShort = TestOdoo.params.lang.split('_')[0];
            
        // charge le formulaire dans la div TestOdooPlugin et déclenche le module
        TestOdoo.loadPhp($);
    });
};

TestOdoo.loadPhp = function ($) {
    $('#TestOdooPlugin').css('min-height', '52px');
    $.ajax({
        url: TestOdoo.pluginPath + 'request_form',
        data: TestOdoo.params,
        method:'POST',
        dataType: 'html',
        success: function(data) {
            $('#TestOdooPlugin').html(data);
            TestOdoo.run($);
        },
        error: function(jq, txt, err) {
            $('#TestOdooPlugin').html("ERROR: Could not load form")
        }
    });
};

//charge un javascript externe et déclenche une acion en cas de succès
TestOdoo.getScript = function (url, success) {
    var script = document.createElement('script');
    script.src = url;
    var head = document.getElementsByTagName('head')[0],
    done = false;
    // Ecouteurs d'événement
    script.onload = script.onreadystatechange = function() {
        if (!done && (!this.readyState || this.readyState == 'loaded' || this.readyState == 'complete')) {
        done = true;
            // déclenche la fonction passée en paramètre
            success();
            script.onload = script.onreadystatechange = null;
            head.removeChild(script);
        };
    };
    head.appendChild(script);
};

// charge jQUeryUi si absent
TestOdoo.getJqueryUi = function() {
    if (typeof jQuery.ui == 'undefined') {
        jQuery("head").append("<link rel='stylesheet' type='text/css' href='//ajax.googleapis.com/ajax/libs/jqueryui/1/themes/south-street/jquery-ui.min.css' />");
        TestOdoo.getScript('//ajax.googleapis.com/ajax/libs/jqueryui/1/jquery-ui.min.js', function() {
            TestOdoo.loadJQueryPlugins();
        });
    }else{
        TestOdoo.loadJQueryPlugins();
    }
};

// déclenche la séquence de bootstrap
// Charge jQuery si absent
if (typeof jQuery == 'undefined') {
    TestOdoo.getScript('//ajax.googleapis.com/ajax/libs/jquery/1/jquery.min.js', function() {
        // jQuery est prêt, charge jQueryUi
        TestOdoo.getJqueryUi();
    });
} else { // jQuery déjà présent, charge jQueryUi
    TestOdoo.getJqueryUi();
};