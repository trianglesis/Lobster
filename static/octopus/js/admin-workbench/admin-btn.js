$(document).ready(function () {
    assignAdminButtons()
});

function assignAdminButtons() {
    let p4_info = document.getElementById("p4_info");
    let p4_sync = document.getElementById("p4_sync");
    let p4_sync_force = document.getElementById("p4_sync_force");
    let parse_full = document.getElementById("parse_full");
    let cases_weight = document.getElementById("cases_weight");

    // p4_info.dataset.operation_key = 'p4_info';
    p4_info.addEventListener('click', buttonActivationADDM);

    // p4_sync.dataset.operation_key = 'p4_sync';
    p4_sync.addEventListener('click', buttonActivationADDM);

    // p4_sync_force.dataset.operation_key = 'p4_sync_force';
    p4_sync_force.addEventListener('click', buttonActivationADDM);

    // parse_full.dataset.operation_key = 'parse_full';
    parse_full.addEventListener('click', buttonActivationADDM);

    // cases_weight.dataset.operation_key = 'cases_weight';
    cases_weight.addEventListener('click', buttonActivationADDM);

}