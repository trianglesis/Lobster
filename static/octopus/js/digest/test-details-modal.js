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

        // Run REST get to obtain related case for this test:
        let caseItem = new RESTGetCaseByTestPyPath(caseData, modal, event, fillModalBodyHyperlinksButtons);
    });
});

function fillModalBodyHyperlinksButtons(caseItem, caseData, modal, event) {
    console.table(caseItem);
    console.table(caseData);
    // Update modal view and data with some of case item values:
    caseData.case_id = caseItem.id;
    caseData.cases_ids = caseItem.id;
    caseData.change_ticket = caseItem.change_ticket;
    caseData.change_review = caseItem.change_review;
    caseData.change_user = caseItem.change_user;
    caseData.change = caseItem.change;

    // Fill modal body with divs:
    fillModalBody(modal, caseData);

    let button = getButtonFromEvent(event);
    let addm_name_url = detectADDMSelectorFromContext(button, caseData);
    let tst_status_url = detectTestStatusSelectorFromContext(button, caseData);

    composeLogsHyperlinks(caseData, addm_name_url, tst_status_url);
    assignTestCaseTestButtons(caseData);
    assignTestCaseUnitTestButtons(caseData);
    composeCaseHyperlinks(caseData);
}