/**
 * This is a launcher of modal for pattern test case on pages:
 * -- /octo_tku_patterns/tests_last/
 * -- /octo_tku_patterns/test_details/
 * -- /octo_tku_patterns/test_cases/
 * -- /octo_tku_patterns/test_cases_group/1/
 * -- /user_space/?change_user=USERNAME
 * -- /octo_tku_patterns/found/
 * Here all data for case if present, like ID, Pattern folder change, tickets and metadata from p4.
 * Parse data from table row where modal button was pressed,
 *  - compose hyperlinks to browse case, and detailed logs
 *  Later: assign event listeners to test run buttons.
 */

// import from 'run-tests-modal-toast-test-tables'


$(document).ready(function () {
    $('#actionsModal').on('hidden.bs.modal', function (event) {
        $('#actionsModal').modal('hide');
    });
});



/**
 * Draw modal with case/test info and buttons to browse logs, case and run tests with different modes
 * caseData comes from Global variable after parseTableRowForCaseData!
 */
$(document).ready(function () {
    $('#actionsModal').on('show.bs.modal', function (event) {
        let button = getButtonFromEvent(event);  // Get some context values from modal button 'Actions'
        let relCases = makeCaseTestDataSet(tests_digest_json, button.data('case_id'));
        let modal = document.getElementById("actionsModal");

        // Fill modal body with divs:
        fillModalBodyNew(modal, relCases);
        // Paste hyperlinks on buttons with log views:
        let addm_name_url = detectADDMSelectorFromContext(button, caseData);  // Add addm name anchor to next page
        let tst_status_url = detectTestStatusSelectorFromContext(button, caseData);  // Add tst_status context to href

        composeLogsHyperlinks(caseData, addm_name_url, tst_status_url);  // href for test last -> test logs
        composeCaseHyperlinks(caseData);  // href to case full view
        assignTestCaseTestButtons(caseData);  // Make buttons for test execution with data attrs of case ids
    })
});



/**
 * This is an event listener and toast maker for pattern test cases on page: /octo_tku_patterns/tests_last/
 * Here we have most of case metadata from p4: changes, user, and so on.
 * Use metadata to show toast details.
 * Run POST and GET requests with case ID to run test and check if task added to queue.
 */

// Listen to button user pushed:
// Add event listener to button
$(document).ready(function () {
    eventListenerForCaseTestButtons(testRunPrepareToast);
});


/**
 * Draw toast with selected case/test and fire task to exec test via REST
 * * caseData comes from Global variable after parseTableRowForCaseData!
 * @param testButtonDataset
 */
function testRunPrepareToast(testButtonDataset) {
    // caseData comes from Global variable!
    let toastBase = getToastDraftWithId(caseData);  // Make unique copy of toast draft
    let toastReady = fillToastBodyWithTestAttributes_.fillModalTestModeById(toastBase, caseData, testButtonDataset);  // fill toast with data
    // let toastReady = fillToastBodyWithTestAttributes(toastBase, caseData, testButtonDataset);  // fill toast with data
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    // Check test modes from button dataset
    composeTestDataSet(caseData, testButtonDataset);
    new RESTPostTask(caseData, testButtonDataset, toastBase); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:

    $('#actionsModal').modal('hide');
    $('#' + toastBase.id).toast('show')
}



