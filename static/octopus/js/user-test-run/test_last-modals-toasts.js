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
        relCases = makeCaseTestDataSet(tests_digest_json, button.data('case_id'));
        let modal = document.getElementById("actionsModal");

        // Fill modal body with divs:
        let caseAttrs = [
            'tkn_branch', 'pattern_library', 'pattern_folder_name',
            'case_id', 'change_ticket', 'change_review', 'change_user', 'change', 'test_py_path'];
        fillModalBodyNew(modal, relCases, caseAttrs);
        fillModalBodyTableTestFails(relCases);
        // Paste hyperlinks on buttons with log views:
        let addm_name_url = detectADDMSelectorFromContext(button, relCases);  // Add addm name anchor to next page
        let tst_status_url = detectTestStatusSelectorFromContext(button, relCases);  // Add tst_status context to href

        composeLogsHyperlinksNew(relCases, addm_name_url, tst_status_url);  // href for test last -> test logs
        composeCaseHyperlinksNew(relCases);  // href to case full view
        assignTestCaseTestButtonsNew(relCases);  // Make buttons for test execution with data attrs of case ids
    })
});

$(document).ready(function () {
    eventListenerForCaseTestButtons(testRunPrepareToast);
});

function testRunPrepareToast(testButtonDataset) {
    caseData = relCases[0];
    console.log(caseData);
    // caseData comes from Global variable!
    let toastBase = getToastDraftWithId(caseData);  // Make unique copy of toast draft
    let toastReady = fillToastBodyWithTestAttributes(toastBase, caseData, testButtonDataset);  // fill toast with data
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    // Check test modes from button dataset
    composeTestDataSet(caseData, testButtonDataset);

    console.log("TO REST");
    console.log(testButtonDataset);

    new RESTPostTask(testButtonDataset, toastBase); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:

    $('#actionsModal').modal('hide');
    $('#' + toastBase.id).toast('show')
}
