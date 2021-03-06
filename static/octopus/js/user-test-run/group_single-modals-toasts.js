/**
 * Modal and toast for /octo_tku_patterns/tests_last/ -> Actions
 */

let relCases = [];
let casesIds = [];

$(document).ready(function () {
    $('#actionsModal').on('hidden.bs.modal', function (event) {
        $('#actionsModal').modal('hide');
    });
});

$(document).ready(function () {
    $('#actionsModal').on('show.bs.modal', function (event) {
        let button = getButtonFromEvent(event);  // Get some context values from modal button 'Actions'
        let modal = document.getElementById("actionsModal");

        if (button.data && button.data('run_group_all')) {
            console.log("All cases in group run!");
            relCases = cases_json;
            hideHyperlinks();
            fillModalBodyWithMultipleCases(modal, relCases);
            casesIds = makeMultipleCasesIdsStr(relCases);
            console.log(casesIds);
            assignTestCaseTestButtonsNew(casesIds, true);
        } else {
            console.log("Single case run");
            relCases = makeCaseTestDataSet(cases_json, button.data('case_id'));
            console.log(relCases);
            // Fill modal body with divs:
            let caseAttrs = [
                'tkn_branch', 'pattern_library', 'pattern_folder_name',
                'id', 'case_id', 'change_ticket', 'change_review', 'change_user', 'change', 'test_py_path'];
            fillModalBodyNew(modal, relCases, caseAttrs);
            // Paste hyperlinks on buttons with log views:
            let addm_name_url = detectADDMSelectorFromContext(button, relCases);  // Add addm name anchor to next page
            let tst_status_url = detectTestStatusSelectorFromContext(button, relCases);  // Add tst_status context to href
            composeLogsHyperlinksNew(relCases, addm_name_url, tst_status_url);  // href for test last -> test logs
            composeCaseHyperlinksNew(relCases[0]['id']);  // href to case full view
            assignTestCaseTestButtonsNew(relCases[0]['id']);  // Make buttons for test execution with data attrs of case ids
        }

    })
});

$(document).ready(function () {
    eventListenerForCaseTestButtons(testRunPrepareToast);
});

function testRunPrepareToast(testButtonDataset) {
    console.log(testButtonDataset);
    let toastBase = {'id': 'NoId-UseDefault'};
    // Multiple cases run:
    if (testButtonDataset['multiple_cases']) {
        console.log('Multiple case test run for case group! ' + casesIds);
        toastBase = getToastDraftWithId(undefined, groupId);  // Make unique copy of toast draft
        let toastReady = fillToastBodyWithTestAttributes(toastBase, casesIds, testButtonDataset);  // fill toast with data
        appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
        // Check test modes from button dataset
        let caseData_alt = {'case_id': casesIds};  // Override usual caseData obj with new assigned all cases IDs
        composeTestDataSet(caseData_alt, testButtonDataset);
        // console.log("TO REST");
        // console.log(testButtonDataset);
        new RESTPostTask(testButtonDataset, toastBase); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:
    // Single case run:
    } else {
        console.log('Single case select and run test');
        caseData = relCases[0];
        // caseData comes from Global variable!
        toastBase = getToastDraftWithId(caseData);  // Make unique copy of toast draft
        let toastReady = fillToastBodyWithTestAttributes(toastBase, caseData, testButtonDataset);  // fill toast with data
        appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
        // Check test modes from button dataset
        composeTestDataSet(caseData, testButtonDataset);
        // console.log("TO REST");
        // console.log(testButtonDataset);
        new RESTPostTask(testButtonDataset, toastBase); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:
    }

    $('#actionsModal').modal('hide');
    $('#' + toastBase.id).toast('show')
}
