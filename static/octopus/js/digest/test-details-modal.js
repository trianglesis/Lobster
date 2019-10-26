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
        console.log("Showing modal!");
        // let modal_ = $(this);
        let modal = document.getElementById("actionsModal");
        // console.log("Parsing table for CaseData");
        let tableRow = getTableRowFromEvent(event);
        let caseData = parseTableRowForCaseData(tableRow);
        // console.table(caseData);

        // Run REST get to obtain related case for this test:
        // console.log("GET REST for full case info!");
        new RESTGetCaseByTestPyPath(caseData, modal, event, fillModalBodyHyperlinksButtons);
    });
});

function fillModalBodyHyperlinksButtons(caseItem, caseData, modal, event) {
    // console.table(caseItem);
    // console.table(caseData);
    // Update modal view and data with some of case item values:
    caseData.case_id = caseItem.id;
    caseData.change_ticket = caseItem.change_ticket;
    caseData.change_review = caseItem.change_review;
    caseData.change_user = caseItem.change_user;
    caseData.change = caseItem.change;
    // console.log("FINISH GET REST for full case info!");
    // console.table(caseItem);

    let button = getButtonFromEvent(event);
    let addm_name_url = detectADDMSelectorFromContext(button, caseData);
    let tst_status_url = detectTestStatusSelectorFromContext(button, caseData);

    composeLogsHyperlinks(caseData, addm_name_url, tst_status_url);

    let buttonData = {
        cases_ids: caseItem.id,
        tst_class: caseData.tst_class,
        tst_name: caseData.tst_name,
    };
    assignTestCaseTestButtons(buttonData);
    assignTestCaseUnitTestButtons(buttonData);

    if (caseData.tst_class && caseData.tst_name) {
    } else {
        console.log("Do not set unit case button, no test_class+name attributes were found!")
    }

    composeCaseHyperlinks(caseData);
    // Fill modal body with divs:
    // console.log("Now filling modal body with caseData");
    fillModalBody(modal, caseData);
    // console.log('Modal body is ready now!')
}