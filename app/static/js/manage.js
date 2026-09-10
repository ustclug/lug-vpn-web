'use strict'

$(document).ready(function () {
    $('#applying_list .btn-success').on('click', function (e) {
        e.preventDefault();
        $(this).attr("disabled", true);
        $(this).text("Please wait...");
        $(this).closest("form").submit();
    });
});
