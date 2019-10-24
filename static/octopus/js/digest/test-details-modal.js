/**
 * This is a modal launcher for page /octo_tku_patterns/test_details/
 * Here we have no case metadata or case_id, use test log details to compose modal body?
 */

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

        // Run REST get to obtain related case for this test:
        let caseItem = RESTGetCaseByTestPyPath(caseData.test_py_path);
        console.table(caseItem);

        // Fill modal body with divs:
        fillModalBody(modal, caseData);

        // Paste hypelinks on buttons with log views:
        let button = getButtonFromEvent(event);
        let addm_name_url = detectADDMSelectorFromContext(button, caseData);
        let tst_status_url = detectTestStatusSelectorFromContext(button, caseData);

        composeLogsHyperlinks(caseData, addm_name_url, tst_status_url);
        assignTestCaseTestButtons(caseData);
        assignTestCaseUnitTestButtons(caseData);
        composeCaseHyperlinks(caseData);
    });

});