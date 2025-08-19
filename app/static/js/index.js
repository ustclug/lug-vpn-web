'use strict'

$(document).ready(function () {
    $('.regen').on('click', function (e) {
        e.preventDefault();
        if (confirm('Are you sure to regenerate your password?'))
            $(this).closest("form").submit();
    });

    // class="click-to-copy":
    $('.click-to-copy').on('click', function () {
        var $temp = $("<input>");
        $("body").append($temp);
        $temp.val($(this).text()).select();
        document.execCommand("copy");
        $temp.remove();
    });
});
