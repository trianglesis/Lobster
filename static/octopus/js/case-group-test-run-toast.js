// Listen to button user pushed:
// Add event listener to button
$(document).ready(function () {
    console.log("Toast prepare, wait");
    waitModalButtonsDraw();
});

/**
 * Small timeout to allow modal to be loaded properly
 */
function waitModalButtonsDraw() {
    setTimeout(function () {
        addListeners();
    }, 1000);
}

/**
 * Add listeners to buttons and set initial args
 */
function addListeners() {
    // Test case testing
    let test_wipe_run = document.getElementById("cases-wipe-run");
    let test_p4_run = document.getElementById("cases-p4-run");
    let test_instant_run = document.getElementById("cases-instant-run");

    console.log(test_wipe_run);
    console.log(test_p4_run);
    console.log(test_instant_run);

    if (test_wipe_run) {
        test_wipe_run.addEventListener("click", function () {
            // let testArg = {wipe: 1, cases_ids: this.dataset.cases_ids};
            // console.log("Push: test_wipe_run");
            composeToastSteps(test_wipe_run.dataset)
        });
    }
    if (test_p4_run) {
        test_p4_run.addEventListener("click", function () {
            // let testArg = {refresh: 1, cases_ids: this.dataset.cases_ids};
            // console.log("Push: test_p4_run");
            composeToastSteps(test_p4_run.dataset)
        });
    }
    if (test_instant_run) {
        test_instant_run.addEventListener("click", function () {
            // let testArg = {cases_ids: this.dataset.cases_ids};
            // console.log("Push: test_instant_run");
            composeToastSteps(test_instant_run.dataset)
        });
    }
    console.log("Toast ready");
}

/**
 * Making a copy of toast draft HTML and assign new copy with unique case ID
 * TODO: If no case_id found - use unique case values set. (tkn_branch, library, patt_folder etc) or use test ID?
 * @param caseData
 * @returns {Node}
 */
function getToastDraft(caseData) {
    let toastDraft = document.getElementById('toastDraft'); // Get draft toast from page foot
    let toastBase = toastDraft.children[0].cloneNode(true);  // Toast object

    // Set toast values:
    toastBase.setAttribute('data-delay', 30000); // 30 sec. Wait to task mod
    // Make a toast with stale ID, there is a group execution, we don't need multiple toasts
    toastBase.id = 'case-group-toast-test-run';
    caseData.toastId = toastBase.id;

    // Toast elements:
    // toastBase.childNodes[1];  // toast-header
    // toastBase.childNodes[3];  // toast-body
    return toastBase
}

/**
 * Fill new toast copy body with attributes from case to show which test has been started and what pattern.
 * @param toastBase
 * @param testArg
 * @returns {*}
 */
function fillToastBody(toastBase, testArg) {
    let cases_ids = document.createElement('div');  // toast-body
    cases_ids.setAttribute('id', 'cases_ids');
    cases_ids.innerText = `Cases ids: ${testArg.cases_ids}`;
    toastBase.childNodes[3].appendChild(cases_ids);
    let test_mode = document.createElement('div');  // toast-body
    test_mode.setAttribute('id', 'test_mode');
    if (testArg.wipe) {
        test_mode.innerText = `Wipe latest logs`;
        toastBase.childNodes[3].appendChild(test_mode);
    } else if (testArg.refresh) {
        test_mode.innerText = `Run p4 sync, wipe latest logs`;
        toastBase.childNodes[3].appendChild(test_mode);
    } else {
        test_mode.innerText = `Instant run, keep logs, no p4 sync`;
        toastBase.childNodes[3].appendChild(test_mode);
    }
    return toastBase
}

/**
 * Get published toast by it's ID. We're assigning id by case_id, so it should be same.
 * @param toastReady
 */
function appendToastToStack(toastReady) {
    // Append new toast to toast stack container:
    document.getElementById('toastStack').appendChild(toastReady);
}

/**
 * Make toast show and modal object hide.
 * @param toastID
 */
function showToast(toastID) {
    $('#mulCasesModal').modal('hide');
    $('#' + toastID).toast('show')
}

/**
 * Already published toast now modifying with task id from POST request
 * @param testArg
 */
function toastModifyPre(testArg) {
    let toastPublished = document.getElementById(testArg.toastId);
    let task_id = document.createElement('div');  // toast-body
    task_id.setAttribute('id', 'task_id');
    task_id.innerText = `task: ${testArg.task_id}`;
    toastPublished.childNodes[3].appendChild(task_id);
}

/**
 * Already published toast now modifying with new data: when task has been added and GET request return it's data
 * NOTE: It does not work while task is processing. Only when finished and saved to DB
 * @param caseData
 */
function toastModifySuccess(caseData) {
    let toastPublished = document.getElementById(caseData.toastId);
    let task_status = document.createElement('div');  // toast-body
    task_status.setAttribute('id', 'task_status');
    // console.log("Modifying toast with task:");
    // console.table(caseData);
    let task = caseData.task_obj;
    if (task.state) {
        task_status.innerText = `task: ${task.status} - ${task.state}`;
    } else {
        if (task.status === 'FAILURE') {
            task_status.innerText = `task: ${task.status} - please check!`;
        } else {
            task_status.innerText = `task: ${task.status} - wait in queue...`;
        }
    }
    toastPublished.childNodes[3].appendChild(task_status);
}

/**
 * REST call to run user test task. Return task_id by default, if added.
 * @param testArg
 * @returns {*}
 * @constructor
 */
function RESTPostTask(testArg) {
    // console.log(`POST user test: ${caseData}`);
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/x-www-form-urlencoded",
        url: "/octo_tku_patterns/user_test_add/",
        data: testArg,
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            // console.log(`POST result: ${result}`);
            if (result.task_id) {
                testArg.task_id = result.task_id;
                // console.log("testArg after POST: ");
                // console.table(testArg);
                // On success - run get task status:
                toastModifyPre(testArg);
                waitResult(testArg);
            } else {
                console.log("Task POST send, but haven't been added. No task_id in result!")
            }
        },
        "error": function () {
            console.log("POST TASK ERROR, something goes wrong...")
        },
    });
    return testArg;
}

/**
 * Timewait, before trying to get task data(status) by it's ID
 * @param testArg
 */
function waitResult(testArg) {
    setTimeout(function () {
        new RESTGetTask(testArg);
    }, 5000);

}

/**
 * REST GET request to obtain task status and data by task_id.
 * If request is 'success' - try to modify published toast with same ID as case(or test) to show current task status
 * @param testArg
 * @returns {*}
 * @constructor
 */
function RESTGetTask(testArg) {
    // console.log(`GET user test task by id: ${caseData.task_id}`);
    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/octo_tku_patterns/user_test_add/",
        data: {task_id: testArg.task_id},
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            // console.log(`GET result: ${result}`);
            // console.table(result[0]);
            let task = result[0];
            if (task && task.status) {
                testArg.task_obj = task;
                // console.log("testArg right after GET");
                // console.table(testArg);
                // On success - run toast modify:
                toastModifySuccess(testArg);
            } else {
                console.log("Task GET failed, no task found or no status");
            }
        },
        "error": function () {
            console.log("GET TASK ERROR, something goes wrong...");
        },
    });
    return testArg;
}

/**
 * Run logic of firing task from modal button and toast show and modify.
 */
function composeToastSteps(testArg) {
    console.log("caseData INITIAL: ");
    console.table(testArg);

    let toastBase = getToastDraft(testArg);  // Make unique copy of toast draft
    let toastReady = fillToastBody(toastBase, testArg);  // fill toast with data
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    new RESTPostTask(testArg); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:

    showToast(testArg.toastId); // Make toast visible
}
