/**
 * Collect all selected tests
 * @param elementId
 * @returns {[]}
 */
function testTableCheckBoxesCollect(elementId) {
    let selectedTestsCaseIDs = [];
    let checkBoxes = document.getElementsByClassName("test-last-rerun-select");

    for (let checkbox of checkBoxes) {
        if (checkbox.checked) {
            if (selectedTestsCaseIDs.includes(checkbox.value)) {
                console.log('Already selected');
                checkbox.checked = false;
            } else {
                selectedTestsCaseIDs.push(checkbox.value);
                checkbox.checked = false;
            }
        }
    }
    if (selectedTestsCaseIDs.length) {
        console.log(`selectedTestsCaseIDs ${selectedTestsCaseIDs}`);
    }
    return selectedTestsCaseIDs;
}

function testLastSelectedGenerateRequest(event) {
    let runSelectedTests = event.currentTarget;
    let caseFullData = {};

    let selectedTestsCaseIDs = testTableCheckBoxesCollect('test-last-rerun-select');
    runSelectedTests.dataset.cases_ids = selectedTestsCaseIDs.join(',');
    console.log(runSelectedTests.dataset);

    // Maybe assign this summarized object to another var, so we can show full dataSet, but POST only needed for test:
    console.log('caseFullData');
    console.table(caseFullData);

    let toastBase = getToastDraftWithId(runSelectedTests);  // Make unique copy of toast draft
    let toastReady = fillToastBodyWithTestAttributes(toastBase, runSelectedTests);  // fill toast with data
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:

    new RESTPostTask(caseFullData, runSelectedTests.dataset); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:
    showToast(runSelectedTests.toastId); // Make toast visible
}


/**
 * Collect all selected tests from table /octo_tku_patterns/tests_last/
 * and re-execute all cases by id list
 */
$(document).ready(function () {
    let ReRunSelectedTests = document.getElementById('TestLast-RunSelected');
    ReRunSelectedTests.removeEventListener('click', testLastSelectedGenerateRequest);
    ReRunSelectedTests.addEventListener("click", testLastSelectedGenerateRequest);
});