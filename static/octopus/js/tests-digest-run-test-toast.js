// Listen to button user pushed:
// Add event listener to button
$(document).ready(function () {
    console.log("Toast prepare");
    // Test case testing
    let test_wipe_run = document.getElementById("wipe-run");
    let test_p4_run = document.getElementById("p4-run");
    let test_instant_run = document.getElementById("instant-run");

    if (test_wipe_run) {
        test_wipe_run.addEventListener("click", function () {
            composeToastSteps(test_wipe_run.dataset)
        });
    }
    if (test_p4_run) {
        test_p4_run.addEventListener("click", function () {
            composeToastSteps(test_p4_run.dataset)
        });
    }
    if (test_instant_run) {
        test_instant_run.addEventListener("click", function () {
            composeToastSteps(test_instant_run.dataset)
        });
    }

    // Case Unit testing:
    let unit_wipe_run  = document.getElementById("unit-wipe-run");
    let unit_p4_run  = document.getElementById("unit-p4-run");
    let unit_instant_run  = document.getElementById("unit-instant-run");

    if (unit_wipe_run) {
        unit_wipe_run.addEventListener("click", function () {
            composeToastSteps(unit_wipe_run.dataset)
        });
    }
    if (unit_p4_run) {
        unit_p4_run.addEventListener("click", function () {
            composeToastSteps(unit_p4_run.dataset)
        });
    }
    if (unit_instant_run) {
        unit_instant_run.addEventListener("click", function () {
            composeToastSteps(unit_instant_run.dataset)
        });
    }

    // Listen for case meta if possible:
    let caseMeta_wipe_run  = document.getElementById("wipe-run-case-meta");
    let caseMeta_p4_run  = document.getElementById("p4-run-case-meta");
    let caseMeta_instant_run  = document.getElementById("instant-run-case-meta");

    if (caseMeta_wipe_run) {
        caseMeta_wipe_run.addEventListener("click", function () {
            composeToastSteps(caseMeta_wipe_run.dataset)
        });
    }
    if (caseMeta_p4_run) {
        caseMeta_p4_run.addEventListener("click", function () {
            composeToastSteps(caseMeta_p4_run.dataset)
        });
    }
    if (caseMeta_instant_run) {
        caseMeta_instant_run.addEventListener("click", function () {
            composeToastSteps(caseMeta_instant_run.dataset)
        });
    }

    console.log("Toast ready");
});

/**
 * Try to get modal body with assigned test case attributes in it.
 * Attributes were added by: static/octopus/js/test-actions-modal.js
 * @param modalBody
 * @returns {Object}
 */
function parseModalBody(modalBody) {
    let modalBodyChildren = modalBody.childNodes[3].children;
    let caseData = new Object({
        tkn_branch: '',
        pattern_library: '',
        pattern_folder_name: '',
        case_id: modalBodyChildren['case_id'].textContent,
        test_id: modalBodyChildren['test_id'].textContent,
        cases_ids: '',
        change_ticket: '',
        change_review: '',
        change_user: '',
        change: '',
    });

    if (modalBodyChildren['tkn_branch'].textContent && modalBodyChildren['pattern_library'].textContent) {
        caseData.tkn_branch = modalBodyChildren['tkn_branch'].textContent;
        caseData.pattern_library = modalBodyChildren['pattern_library'].textContent;
        caseData.pattern_folder_name = modalBodyChildren['pattern_folder_name'].textContent;
    } else if (modalBodyChildren['case_id'].textContent) {
        console.log("This is not a pattern related case, use case ID to select and run test.");
        caseData.cases_ids = modalBodyChildren['case_id'].textContent;
    } else {
        console.log("TODO: Assign other selectables by: change_ticket, change_review, change_user, change(p4) ");
    }

    return caseData
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
    // Assign new toast copy a value ID based on item ID (case id or case unique attrs)
    if (caseData.case_id) {
        toastBase.id = caseData.case_id;
        caseData.toastId = toastBase.id;
    } else if (caseData.test_id) {
        toastBase.id = caseData.test_id;
        caseData.toastId = toastBase.id;
    } else {
        toastBase.id = `${caseData.tkn_branch}_${caseData.pattern_library}_${caseData.pattern_folder_name}`;
        caseData.toastId = toastBase.id;
    }

    // Toast elements:
    // toastBase.childNodes[1];  // toast-header
    // toastBase.childNodes[3];  // toast-body
    return toastBase
}

/**
 * Fill new toast copy body with attributes from case to show which test has been started and what pattern.
 * @param toastBase
 * @param caseData
 * @returns {*}
 */
function fillToastBody(toastBase, caseData) {
    let metaData = ['change_ticket', 'change_review', 'change_user', 'change'];
    let showPattern = true;

    for (const [key, value] of Object.entries(caseData)) {
        if (metaData.indexOf(key) > -1) {
            if (value) {
                console.log(`Key is in extras: ${key} val: ${value}`);
                // Remove cases_ids, because we want to test cases related on metadata only:
                let metadata = document.createElement('div');  // toast-body
                metadata.setAttribute('id', 'testOnMetadata');
                metadata.innerText = `Test all, where ${key} = ${value}`;
                toastBase.childNodes[3].appendChild(metadata);
                showPattern = false;
            }
        }
    }

    if (showPattern) {
        // When no metadata key,values found, just keep caseData with current keys.
        // They're usually patterns attributes or cases_ids.
        let tknBranchPattLib = document.createElement('div');  // toast-body
        let patternDirectory = document.createElement('div');  // toast-body

        tknBranchPattLib.setAttribute('id', 'tknBranchPattLib');
        patternDirectory.setAttribute('id', 'patternDirectory');

        tknBranchPattLib.innerText = `${caseData.tkn_branch} / ${caseData.pattern_library}`;
        patternDirectory.innerText = caseData.pattern_folder_name;

        toastBase.childNodes[3].appendChild(tknBranchPattLib);
        toastBase.childNodes[3].appendChild(patternDirectory);
    }

    let test_mode = document.createElement('div');  // toast-body
    test_mode.setAttribute('id', 'test_mode');
    if (caseData.wipe) {
        test_mode.innerText = `Wipe latest logs`;
        toastBase.childNodes[3].appendChild(test_mode);
    } else if (caseData.refresh) {
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
    $('#actionsModal').modal('hide');
    $('#' + toastID).toast('show')
}

/**
 * Already published toast now modifying with task id from POST request
 * @param caseData
 */
function toastModifyPre(caseData) {
    let toastPublished = document.getElementById(caseData.toastId);
    let task_id = document.createElement('div');  // toast-body
    task_id.setAttribute('id', 'task_id');
    task_id.innerText = `task: ${caseData.task_id}`;
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

function composePostData(caseData) {
    // console.log("Final caseData used to run test task: ");
    // console.table(caseData);
    let metaData = ['change_ticket', 'change_review', 'change_user', 'change'];
    for (const [key, value] of Object.entries(caseData)) {
        if (metaData.indexOf(key) > -1 ) {
            if (value) {
                console.log(`Key is in extras: ${key} val: ${value}`);
                // Remove cases_ids, because we want to test cases related on metadata only:
                delete caseData.cases_ids;
                delete caseData.tkn_branch;
                delete caseData.pattern_library;
                delete caseData.pattern_folder_name;
            } else {
                // When no metadata key,values found, just keep caseData with current keys.
                // They're usually patterns attributes or cases_ids.
            }
        }
    }
    // console.log("postData ready to be POSTed");
    // console.table(caseData);
    return caseData
}

/**
 * REST call to run user test task. Return task_id by default, if added.
 * @param caseData
 * @returns {*}
 * @constructor
 */
function RESTPostTask(caseData) {
    console.log(`POST user test: `);
    console.table(caseData);
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/x-www-form-urlencoded",
        url: "/octo_tku_patterns/user_test_add/",
        data: caseData,
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            // console.log(`POST result: ${result}`);
            if (result.task_id) {
                caseData.task_id = result.task_id;
                // console.log("caseData after POST: ");
                // console.table(caseData);
                // On success - run get task status:
                toastModifyPre(caseData);
                waitResult(caseData);
            } else {
                console.log("Task POST send, but haven't been added. No task_id in result!")
            }
        },
        "error": function () {
            console.log("POST TASK ERROR, something goes wrong...")
        },
    });
    return caseData;
}

/**
 * Timewait, before trying to get task data(status) by it's ID
 * @param caseData
 */
function waitResult(caseData) {
    setTimeout(function () {
        new RESTGetTask(caseData);
    }, 5000);

}

/**
 * REST GET request to obtain task status and data by task_id.
 * If request is 'success' - try to modify published toast with same ID as case(or test) to show current task status
 * @param caseData
 * @returns {*}
 * @constructor
 */
function RESTGetTask(caseData) {
    // console.log(`GET user test task by id: ${caseData.task_id}`);
    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/octo_tku_patterns/user_test_add/",
        data: {task_id: caseData.task_id},
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            // console.log(`GET result: ${result}`);
            // console.table(result[0]);
            let task = result[0];
            if (task && task.status) {
                caseData.task_obj = task;
                // console.log("caseData right after GET");
                // console.table(caseData);
                // On success - run toast modify:
                toastModifySuccess(caseData);
            } else {
                console.log("Task GET failed, no task found or no status");
            }
        },
        "error": function () {
            console.log("GET TASK ERROR, something goes wrong...");
        },
    });
    return caseData;
}

/**
 * Run logic of firing task from modal button and toast show and modify.
 */
function composeToastSteps(buttonDataset) {
    // let modalBody = this.parentNode.parentNode.parentNode;  // To modal body
    let modalBody = document.getElementById('actionsModal').childNodes[1].childNodes[1].childNodes[3];  // To modal body

    // console.log("Initial button dataset: ");
    // console.table(buttonDataset);

    let caseData = parseModalBody(modalBody);  // parse modal body

    Object.assign(caseData, buttonDataset);
    // console.log("caseData INITIAL: ");
    // console.table(caseData);

    let toastBase = getToastDraft(caseData);  // Make unique copy of toast draft
    let toastReady = fillToastBody(toastBase, caseData);  // fill toast with data
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:

    composePostData(caseData);

    new RESTPostTask(caseData); //  Now, keeping our toast ID in memory, make a request to GET actual task_id status:
    showToast(caseData.toastId); // Make toast visible
}
