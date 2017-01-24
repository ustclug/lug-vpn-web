'use strict'

jQuery.fn.dataTable.ext.type.order['file-size-pre'] = function ( data ) {
    var matches = data.match( /^(\d+(?:\.\d+)?)\s*([a-z]+)/i );
    var multipliers = {
        bytes:  1,
        b:  1,
        kb: 1000,
        kib: 1024,
        mb: 1000000,
        mib: 1048576,
        gb: 1000000000,
        gib: 1073741824,
        tb: 1000000000000,
        tib: 1099511627776,
        pb: 1000000000000000,
        pib: 1125899906842624
    };
    if (matches) {
        var multiplier = multipliers[matches[2].toLowerCase()];
        return parseFloat( matches[1] ) * multiplier;
    } else {
        return -1;
    };
};

$(document).ready(function () {
    $('#applying_list .btn-success').on('click', function (e) {
        e.preventDefault();
        $(this).attr("disabled", true);
        $(this).text("Please wait...");
        $(this).closest("form").submit();
    });
    if(!$.fn.dataTable.isDataTable('#all_users'))
        $('#all_users').DataTable({
            colReorder: true,
            responsive: true,
            select: true,
            columnDefs: [
                { type: 'file-size', targets: 3 },
                { type: 'file-size', targets: 4 }
            ],
            aaSorting: []
        });
    if(!$.fn.dataTable.isDataTable('#rejected_users'))
        $('#rejected_users').DataTable({
            colReorder: true,
            responsive: true,
            select: true,
            columnDefs: [
                { "width": "40%", "targets": 3 }
            ],
            aaSorting: []
        });
});
