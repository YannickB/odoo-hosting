$(document).ready(function () {
    $('.oe_website_clouder_instance').each(function () {
        $('.a-submit').off('click').on('click', function () {
            $(this).closest('form').submit();
        });
        $(this).on('change', "select[name='country_id']", function () {
            var $select = $("select[name='state_id']");
            $select.find("option:not(:first)").hide();
            var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
            $select.parent().toggle(nb>1);
        });
        $(this).find("select[name='country_id']").change();
    });
});
