/**
 * Modal and toast for /octo_tku_patterns/tests_last/ -> Actions
 */

let relCases = [];

$(document).ready(function () {
    $('#actionsModal').on('hidden.bs.modal', function (event) {
        $('#actionsModal').modal('hide');
    });
});

$(document).ready(function () {
    $('#actionsModal').on('show.bs.modal', function (event) {
        let button = getButtonFromEvent(event);  // Get some context values from modal button 'Actions'
        relCases = makeCaseTestDataSet(cases_json, button.data('case_id'), button.data('test_py_path'));
        let modal = document.getElementById("actionsModal");

        // Fill modal body with divs:
        let caseAttrs = [
            'tkn_branch', 'pattern_library', 'pattern_folder_name',
            'id', 'case_id', 'change_ticket', 'change_review', 'change_user', 'change', 'test_py_path'];
        fillModalBodyNew(modal, relCases, caseAttrs);
        assignTestCaseTestButtonsNew(relCases[0]['id']);  // Make buttons for test execution with data attrs of case ids
    })
});

$(document).ready(function () {
    eventListenerForCaseTestButtons(testRunPrepareToast);
});

function testRunPrepareToast(testButtonDataset) {
    caseData = relCases[0];
    // console.log(caseData);
    // caseData comes from Global variable!
    let toastBase = getToastDraftWithId(caseData);  // Make unique copy of toast draft
    let toastReady = fillToastBodyWithTestAttributes(toastBase, caseData, testButtonDataset);  // fill toast with data
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    // Check test modes from button dataset
    composeTestDataSet(caseData, testButtonDataset);

    // console.log("TO REST");
    // console.log(testButtonDataset);

    new RESTPostTask(testButtonDataset, toastBase); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:

    $('#actionsModal').modal('hide');
    $('#' + toastBase.id).toast('show')
}
