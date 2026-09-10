'use strict'

DataTable.type('file-size', {
    order: {
        pre: function (data) {
            var matches = data.match(/^(\d+(?:\.\d+)?)\s*([a-z]+)/i);
            var multipliers = {
                bytes: 1,
                b: 1,
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

            if (!matches) {
                return -1;
            }

            return parseFloat(matches[1]) * multipliers[matches[2].toLowerCase()];
        }
    }
});

$(document).ready(function () {
    $('#applying_list .btn-success').on('click', function (e) {
        e.preventDefault();
        $(this).attr("disabled", true);
        $(this).text("Please wait...");
        $(this).closest("form").submit();
    });
    if (!DataTable.isDataTable('#all_users')) {
        new DataTable('#all_users', {
            colReorder: true,
            responsive: true,
            select: true,
            columnDefs: [
                { type: 'file-size', targets: 3 },
                { type: 'file-size', targets: 4 }
            ],
            order: []
        });
    }
    if (!DataTable.isDataTable('#rejected_users')) {
        new DataTable('#rejected_users', {
            colReorder: true,
            responsive: true,
            select: true,
            columnDefs: [
                { width: '40%', targets: 3 }
            ],
            order: []
        });
    }
});
