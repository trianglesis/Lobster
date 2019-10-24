$(document).ready(function () {
    console.log("Tab active nav");
    if (location.hash !== '') $('a[href="' + location.hash + '"]').tab('show');
    return $('a[data-toggle="tab"]').on('shown', function (e) {
        return location.hash = $(e.target).attr('href').substr(1);
    });
});