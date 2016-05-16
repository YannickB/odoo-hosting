$(document).ready(function () {
    $('.oe_website_clouder_instance').each(function () {
        var oe_website_sale = this;
        $('.a-submit').off('click').on('click', function () {
            $(this).closest('form').submit();
        });
        $(oe_website_sale).on('change', "select[name='country_id']", function () {
            var $select = $("select[name='state_id']");
            $select.find("option:not(:first)").hide();
            var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
            $select.parent().toggle(nb>1);
        });
        $(oe_website_sale).find("select[name='country_id']").change();
    });
});
