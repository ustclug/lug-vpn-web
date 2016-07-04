'use strict'

$(document).ready(function () {
    if($('#month_traffic').length){
        var url='/traffic/';
        if($('#userid').length)
            url+='?id='+$('#userid').text();
        $.get(url).done(function(data){
            var traffic = JSON.parse(data);
            var chart = new CanvasJS.Chart("last_month_traffic",
            {
                title: {
                    text: "Last Month (MiB)"
                },
                data: [
                {
                    type: "line",
                    color: "darkred",
                    showInLegend: true,
                    legendText: "Upload",
                    dataPoints: traffic['last_month_upload']
                },
                {
                    type: "line",
                    color: "darkgreen",
                    showInLegend: true,
                    legendText: "Download",
                    dataPoints: traffic['last_month_download']
                }
                ],
                axisX:{
                    interval: 1,
                }
            });
            chart.render();
            chart = new CanvasJS.Chart("month_traffic",
            {
                title: {
                    text: "This Month (MiB)"
                },
                data: [
                {
                    type: "line",
                    color: "darkred",
                    showInLegend: true,
                    legendText: "Upload",
                    dataPoints: traffic['month_upload']
                },
                {
                    type: "line",
                    color: "darkgreen",
                    showInLegend: true,
                    legendText: "Download",
                    dataPoints: traffic['month_download']
                }
                ],
                axisX:{
                    interval: 1,
                }
            });
            chart.render();
        });
    }
});
