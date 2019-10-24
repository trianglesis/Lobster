$(document).ready(function () {
    $('[data-toggle="tooltip"]').tooltip();
});
$(document).ready(function () {
    $('[data-toggle="popover"]').popover();
});
$(document).ready(function () {
    $('[data-toggle="hover"]').popover({
        trigger: 'hover'
    });
});