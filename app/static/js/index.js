'use strict'

$(document).ready(function () {
    $('.regen').on('click', function (e) {
        e.preventDefault();
        if(confirm('Are you sure to regenerate your password?'))
            $(this).closest("form").submit();
    });
});
