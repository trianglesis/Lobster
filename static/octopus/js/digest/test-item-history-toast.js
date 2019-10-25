/**
 * This is an event listener and toast maker for pattern test cases (only test sorted) on page: /octo_tku_patterns/test_details/
 * Here we have not case metadata info. Use test details to compose task request.
 * Run POST and GET requests with test data?
 */

// Listen to button user pushed:
// Add event listener to button
$(document).ready(function () {
    console.log("Toast prepare");

    eventListenerForCaseTestButtons(testRunPrepareToast);
    eventListenerForCaseUnitTestButtons(testRunPrepareToast);

    console.log("Toast ready");
});


function testRunPrepareToast(testButtonDataset) {
    // console.log('testRunPrepareToast got dataset');
    // console.table(testButtonDataset);

    let modalBody = document.getElementById('actionsModal').childNodes[1].childNodes[1].childNodes[3];  // To modal body
    // console.table(modalBody);
    let caseData = parseModalBodyForCaseData(modalBody);  // parse modal body
    // console.log('caseData');
    // console.table(caseData);

    // Maybe assign this summarized object to another var, so we can show full dataSet, but POST only needed for test:
    let caseFullData = Object.assign(caseData, testButtonDataset);
    // console.log('caseFullData');
    // console.table(caseFullData);
    let toastBase = getToastDraftWithId(caseFullData);  // Make unique copy of toast draft
    let toastReady = fillToastBodyWithTestAttributes(toastBase, caseFullData);  // fill toast with data
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:

    // console.log('testButtonDataset');
    // console.table(testButtonDataset);

    new RESTPostTask(caseFullData, testButtonDataset); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:
    showToast(caseData.toastId); // Make toast visible
}