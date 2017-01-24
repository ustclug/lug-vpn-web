'use strict'

$(document).ready(function () {
    $('form').on('submit', function (e) {
        e.preventDefault();
        $('#submit_btn').attr("disabled", true);
        $('#submit_btn').attr("value", "Please wait...");
        this.submit();
    });
});

