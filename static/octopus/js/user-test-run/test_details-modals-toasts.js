/**
 * Modal and toast for /octo_tku_patterns/test_details/ -> Actions
 */

let relCasesTestLogs = [];
let caseDataREST = [];
let modal = '';
let button = '';
button.data = function (testId) {
    return undefined;
};

/**
 * Close modal
 */
$(document).ready(function () {
    $('#actionsModal').on('hidden.bs.modal', function (event) {
        $('#actionsModal').modal('hide');
    });
});

/**
 * Show modal and run following operations:
 * - get pushed button and get id of test or case, then go through JSON data and get only items with according ID
 * - get modal HTMLObject
 * - run REST to get related testCase from test.py path attribute of current test result item
 */
$(document).ready(function () {
    $('#actionsModal').on('show.bs.modal', function (event) {
        button = getButtonFromEvent(event);  // Get some context values from modal button 'Actions'
        relCasesTestLogs = makeCaseTestDataSet(tests_digest_json, button.data('test_id'));
        modal = document.getElementById("actionsModal");
        // Run REST get to obtain related case for this test:
        // Use one
        new RESTGetCaseByTestPyPath(relCasesTestLogs[0], fillModalBodyAfterREST);
    })
});

/**
 * Assign event listener for modal buttons by default with simple starting positions.
 */
$(document).ready(function () {
    eventListenerForCaseTestButtons(testRunPrepareToast);
});

/**
 * - fill modal variables with case details
 * - compose href for log view
 * - compose href for case details view
 * - assign data attrs for test case run
 * - assign data attr for test method run
 * @param caseItem
 */
function fillModalBodyAfterREST(caseItem) {
    // Assign REST result case data to this var to use for post task and toast drawing
    caseDataREST = caseItem;
    // We only require case_id key attr for buttons, there is no reason to pass whole data
    let buttonCaseDataSet = {
        'case_id': caseItem['id'],
        'tst_class': relCasesTestLogs[0]['tst_class'],
        'tst_name': relCasesTestLogs[0]['tst_name'],
    };
    console.table(`Using set: ${buttonCaseDataSet}`);

    // Fill modal body with case details after REST:
    let caseAttrs = ['id', 'tkn_branch', 'pattern_library', 'pattern_folder_name', 'test_py_path',
        'change', 'change_user', 'change_review', 'change_ticket', 'change_desc', 'change_time'];
    fillModalBodyNew(modal, caseItem, caseAttrs);

    // Paste hyperlinks on buttons with log views:
    let addm_name_url = detectADDMSelectorFromContext(button, relCasesTestLogs);  // Add addm name anchor to next page
    let tst_status_url = detectTestStatusSelectorFromContext(button, relCasesTestLogs);  // Add tst_status context to href

    composeLogsHyperlinksNew(relCasesTestLogs, addm_name_url, tst_status_url);  // href for test last -> test logs
    composeCaseHyperlinksNew(buttonCaseDataSet['case_id']);  // href to case full view
    assignTestCaseTestButtonsNew(buttonCaseDataSet['case_id']);  // Make buttons for test execution with data attrs of case ids
    assignTestCaseUnitTestButtons(buttonCaseDataSet);
}

/**
 * - get hidden toast draft from page footer, make copy and assign id related to case ot test id
 * - fill toast with case details and test mode attributes
 * - compose shorter dataset for test task run: only test mode and case sel attrs (cases_ids)
 * - run REST to /octo_tku_patterns/user_test_add/
 * - wait for 15 sec
 * - then modify active toast with task confirmation, when task is actually added into the queue, otherwise show error
 * @param testButtonDataset
 */
function testRunPrepareToast(testButtonDataset) {
    // caseData comes from Global variable!
    caseData = caseDataREST;

    let toastBase = getToastDraftWithId(caseData);  // Make unique copy of toast draft
    let toastReady = fillToastBodyWithTestAttributes(toastBase, caseData, testButtonDataset);  // fill toast with data
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:

    // Check test modes from button dataset
    composeTestDataSet(caseData, testButtonDataset);
    new RESTPostTask(testButtonDataset, toastBase); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:
    $('#actionsModal').modal('hide');
    $('#' + toastBase.id).toast('show')
}
