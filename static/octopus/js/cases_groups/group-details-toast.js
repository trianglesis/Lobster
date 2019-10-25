/**
 *
 * Group of test cases toast
 *
 * This is an event listener and toast maker for pattern test cases on page: /octo_tku_patterns/test_cases_group/1/
 * Here we have most of case metadata from p4: changes, user, and so on.
 * Use metadata to show toast details.
 * Run POST and GET requests with case ID to run test and check if task added to queue.
 */

// Listen to button user pushed:
// Add event listener to button
$(document).ready(function () {
    console.log("Toast prepare");

    // Test case use usual way to listen buttons
    eventListenerForCaseTestButtons(testRunPrepareToast);
    // Test cases group 'Run all' buttons listen to:
    eventListenerForCaseGroupButtons(testRunPrepareToast);

    console.log("Toast ready");
});


function testRunPrepareToast(testButtonDataset) {
    let taskIdStorage = {};
    let toastBase = getToastDraftMultipleCases();  // Multiple case toast does not require ID based on cases
    taskIdStorage.toastId = toastBase.id;

    let toastReady = fillToastBodyWithTestAttributes(toastBase, testButtonDataset);  // fill toast with data

    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    new RESTPostTask(taskIdStorage, testButtonDataset); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:
    showToastHideModal(toastBase.id); // Make toast visible and hide modal
    $('#mulCasesModal').modal('hide');
    $('#actionsModal').modal('hide');
}