TestOdoo.pluginPath = 'http://mblaptop:5050/';

TestOdoo.run = function($){
	$('#TestOdooPlugin').css('background', 'none');
	
    $('#ClouderForm').each(function(){
        //Show step 1 by default
        TestOdoo.showStep($, 1);
        
        //Fill form data with already known variables
        $('form').attr('action', TestOdoo.pluginPath + 'submit_form');
        $('input[name="clouder_partner_id"]').val(TestOdoo.params['partner_id']);
        $('input[name="db"]').val(TestOdoo.params['db']);
        
        //Controls the hidden state of the state selector depending on country
        $(this).on('change', "select[name='country_id']", function () {
            var $select = $("select[name='state_id']");
            $select.find("option:not(:first)").hide();
            var nb = $select.find("option[country_id="+($(this).val() || 0)+"]").show().size();
            $select.parent().toggle(nb>1);
        });
        $(this).find("select[name='country_id']").change();
        
        //Buttons handlers
        $('.a-next').off('click').on('click', function () {
            if (!TestOdoo.error_step($, 1)){
                TestOdoo.showStep($, 2);
            }
        });
        $('.a-prev').off('click').on('click', function () {
            TestOdoo.showStep($, 1);
        });
        $('.a-submit').off('click').on('click', function () {
            if (!TestOdoo.error_step($, 2)){
                $(this).closest('form').submit();
            }
        });
    });
	
	
}

TestOdoo.error_step = function($, step){
    var has_error = false;
    var err_class = "has_error";
    if (step == 1){
        $app_select = $('select[name="application_id"]');
        $domain_select = $('select[name="domain_id"]');
        $prefix_input = $('input[name="prefix"]');
        if (!$app_select.val()){
            $app_select.addClass(err_class);
            has_error = true;
        }
        if (!$domain_select.val()){
            $domain_select.addClass(err_class);
            has_error = true;
        }
        if (!$prefix_input.val()){
            $prefix_input.addClass(err_class);
            has_error = true;
        }
    }
    else if (step == 2){
        $name_select = $('input[name="name"]');
        $phone_select = $('input[name="phone"]');
        $email_select = $('input[name="email"]');
        $street2_select = $('input[name="street2"]');
        $city_select = $('input[name="city"]');
        $country_select = $('select[name="country_id"]');
        
        if (!$name_select.val()){
            $name_select.addClass(err_class);
            has_error = true;
        }
        if (!$phone_select.val()){
            $phone_select.addClass(err_class);
            has_error = true;
        }
        if (!$email_select.val()){
            $email_select.addClass(err_class);
            has_error = true;
        }
        if (!$street2_select.val()){
            $street2_select.addClass(err_class);
            has_error = true;
        }
        if (!$city_select.val()){
            $city_select.addClass(err_class);
            has_error = true;
        }
        if (!$country_select.val()){
            $country_select.addClass(err_class);
            has_error = true;
        }
    }
    else {
        has_error = true;
    }
    return has_error;
};

TestOdoo.showStep = function($, step){
	// affiche les champs correspondant à la bonne étape
	$('.CL_Step').hide();
	$('.CL_Step'+step).show();
}

//charge les plugins jQuery et règle les valeurs par défaut
TestOdoo.loadJQueryPlugins = function() {
	jQuery.noConflict(); // évite que notre version de jQuery entre en conflit avec l'hôte
	jQuery(document).ready(function($) {
		//$('#TestOdooPlugin').css('background', 'url('+TestOdoo.loading+') no-repeat center bottom');
		
		TestOdoo.params.langShort = TestOdoo.params.lang.split('_')[0];
			
        // charge le formulaire dans la div TestOdooPlugin et déclenche le module
        TestOdoo.loadPhp($);
	});
}

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
}

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
}

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
}

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