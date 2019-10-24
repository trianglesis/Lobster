$(document).ready(function () {
    $('#actionsModal').on('hidden.bs.modal', function (event) {
        $('#actionsModal').modal('hide');
    });
});

$(document).ready(function () {
    //Opening of modal action
    $('#actionsModal').on('show.bs.modal', function (event) {
        // let modal_ = $(this);
        let modal = document.getElementById("actionsModal");
        let tableRow = getTableRowFromEvent(event);
        let caseData = parseTableRowForCaseData(tableRow);
        console.table(caseData);

        // Fill modal body with divs:
        fillModalBody(modal, caseData);

        // Paste hypelinks on buttons with log views:
        let button = getButtonFromEvent(event);
        let addm_name_url = detectADDMSelectorFromContext(button, caseData);
        let tst_status_url = detectTestStatusSelectorFromContext(button, caseData);

        composeLogsHyperlinks(caseData, addm_name_url, tst_status_url);
        assignTestCaseTestButtons(caseData);
        composeCaseHyperlinks(caseData);
    });

});