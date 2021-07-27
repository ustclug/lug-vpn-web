'use strict'

function jsDateMap(data) {
    return data.map(item => {
        return {
            'x': new Date(item['x']),
            'y': item['y']
        }
    })
}

$(document).ready(function () {
    if($('#month_traffic').length){
        var url='/traffic/';
        if($('#userid').length)
            url+='?id='+$('#userid').text();
        $.get(url).done(function(data){
            var traffic = JSON.parse(data);
            var last_month_chart = new Chart(document.getElementById("last_month_traffic").getContext('2d'),
            {
                type: 'line',
                options: {
                    plugins: {
                        title: {
                            display: true,
                            text: "Last Month (MiB)"
                        }
                    },
                    scales: {
                        xAxes: [{
                            type: 'time',
                            time: {
                                unit: 'day',
                                displayFormats: {
                                    day: "MM-DD"
                                },
                                tooltipFormat: "YYYY-MM-DD"
                            },
                        }],
                        yAxes: [{
                            ticks: {
                                beginAtZero: true
                            }
                        }]
                    }
                },
                data: 
                {
                    datasets: [{
                        data: jsDateMap(traffic['last_month']),
                        label: 'Last Month'
                    }]
                },
            });

            var chart = new Chart(document.getElementById("month_traffic").getContext('2d'),
            {
                type: 'line',
                options: {
                    plugins: {
                        title: {
                            display: true,
                            text: "This Month (MiB)"
                        }
                    },
                    scales: {
                        xAxes: [{
                            type: 'time',
                            time: {
                                unit: 'day',
                                displayFormats: {
                                    day: "MM-DD"
                                },
                                tooltipFormat: "YYYY-MM-DD"
                            },
                        }],
                        yAxes: [{
                            ticks: {
                                beginAtZero: true
                            }
                        }]
                    }
                },
                data: 
                {
                    datasets: [{
                        data: jsDateMap(traffic['month']),
                        label: 'This Month'
                    }]
                },
            });
        });
    }
});
