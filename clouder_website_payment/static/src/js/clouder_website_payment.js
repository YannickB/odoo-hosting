// When choosing an acquirer, display its Pay Now button
var $payment = Clouder.$("#CL_payment>#payment_method");
$payment.on("click", "input[name='acquirer']", function (ev) {
        var payment_id = Clouder.$(ev.currentTarget).val();
        $payment.find("div[data-id]").hide();
        $payment.find("div[data-id='"+payment_id+"']").show();
    })
    .find("input[name='acquirer']:checked").click();

// When clicking on payment button: create the tx using json then continue to the acquirer
$payment.on("click", 'button[type="submit"],button[name="submit"]', function (ev) {
    ev.preventDefault();

    // Make a window while the event is still declared as valid
    var myWindow = window.open(
        Clouder.pluginPath + 'clouder_form/payment_popup_wait?lang=' + Clouder.params['lang'],
        'cl_payment_popup',
        'resizable=1,scrollbars=yes,height=500,width=700'
    );

    ev.stopPropagation();

    var $form = Clouder.$(ev.currentTarget).parents('form');

    // Make the form open in the new window
    $form.attr("target", "cl_payment_popup");

    var acquirer_id = Clouder.$(ev.currentTarget).parents('div[data-id]').first().data('id');
    if (! acquirer_id) {
        return false;
    }
    Clouder.loading(true, $payment);
    Clouder.$.ajax({
        url: Clouder.pluginPath + 'clouder_form/submit_acquirer',
        data: {
            'clws_id': Clouder.clws_id,
            'acquirer_id': acquirer_id,
            'lang': Clouder.params['lang']
        },
        method: 'POST', type: 'POST'
        cache: false,
        dataType: 'html',
        success: function(data) {
            Clouder.readresponse(JSON.parse(data), false);
            Clouder.loading(false, $payment);
            $payment.hide();
            $form.submit();
        },
        error: function(h, t, e){
            Clouder.loading(false, $payment);
        }
    });
});
