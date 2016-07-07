// When choosing an acquirer, display its Pay Now button
var $payment = Clouder.$("#CL_payment>#payment_method");
$payment.on("click", "input[name='acquirer']", function (ev) {
        var payment_id = Clouder.$(ev.currentTarget).val();
        $payment.find("#CL_payment>#payment_method>div.oe_sale_acquirer_button[data-id]").hide();
        $payment.find("#CL_payment>div.oe_sale_acquirer_button[data-id='"+payment_id+"']").show();
    })
    .find("input[name='acquirer']:checked").click();

// When clicking on payment button: create the tx using json then continue to the acquirer
$payment.on("click", 'button[type="submit"],button[name="submit"]', function (ev) {
  ev.preventDefault();
  ev.stopPropagation();
  var $form = Clouder.$(ev.currentTarget).parents('form');
  var acquirer_id = $(ev.currentTarget).parents('div.oe_sale_acquirer_button').first().data('id');
  if (! acquirer_id) {
    return false;
  }
  // TODO: change and implement
  openerp.jsonRpc('/todo/change' + acquirer_id, 'call', {}).then(function (data) {
    $form.submit();
  });
});
