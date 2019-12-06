/**
 * Global CaseData to use elsewhere out
 * @type {Object}
 */
let caseData = new Object({});

/**
 * Methods
 */

/**
 * Try to get modal body with assigned test case attributes in it.
 * Attributes were added by: static/octopus/js/test-actions-modal.js
 * @param modalVariables
 * @returns {Object}
 */
function parseModalVariables(modalVariables) {
    console.log(modalVariables);
    let VarChildren = modalVariables.children;

    let caseData = new Object({
        tkn_branch: '',
        pattern_library: '',
        pattern_folder_name: '',
        case_id: VarChildren['case_id'].textContent,
        test_id: '',
        cases_ids: '',
        change_ticket: '',
        change_review: '',
        change_user: '',
        change: '',
        wipe: '',
        refresh: '',
        test_function: '',
    });

    if (VarChildren['tkn_branch'] && VarChildren['pattern_library']) {
        caseData.tkn_branch = VarChildren['tkn_branch'].textContent;
        caseData.pattern_library = VarChildren['pattern_library'].textContent;
        caseData.pattern_folder_name = VarChildren['pattern_folder_name'].textContent;
    }
    if (VarChildren['case_id']) {
        console.log("This is not a pattern related case, use case ID to select and run test.");
        caseData.cases_ids = VarChildren['case_id'].textContent;
    }
    if (VarChildren['test_id'] && VarChildren['test_id'].textContent) {
        caseData.test_id = VarChildren['test_id'].textContent;
    } else {
        console.log("TODO: Assign other selectables by: change_ticket, change_review, change_user, change(p4) ");
    }

    return caseData
}

/**
 * Make buttons for test run have required attributes to run test:
 * Single test.py modes: wipe-run, p4-run, instant-run
 * @param caseData
 */
function assignTestCaseUnitTestButtons(caseData) {
    // Test case Unit test run:
    let unit_wipe_run = document.getElementById("unit-wipe-run");
    let unit_p4_run = document.getElementById("unit-p4-run");
    let unit_instant_run = document.getElementById("unit-instant-run");

    // Switching visibility of some blocks and block names, when they do not needed:
    let CaseUnitModalButtons = document.getElementsByClassName("case-unit-modal-buttons");
    let TestActionsModalName = document.getElementsByClassName("test-actions-modal-name");
    let SeeLogsHistory = document.getElementById("see-logs-history");

    if (caseData.tst_class && caseData.tst_name) {
        if (CaseUnitModalButtons[0]) {
            CaseUnitModalButtons[0].style.display = 'block';
        }
        if (TestActionsModalName[0]) {
            TestActionsModalName[0].style.display = 'block';
        }
        if (SeeLogsHistory) {
            SeeLogsHistory.style.display = 'block';
        }

        unit_wipe_run.style.display = 'block';
        unit_p4_run.style.display = 'block';
        unit_instant_run.style.display = 'block';

        if (unit_wipe_run) {
            unit_wipe_run.setAttribute(
                'data-cases_ids', caseData.cases_ids);
            unit_wipe_run.setAttribute(
                'data-test_function',
                `${caseData.tst_class}+${caseData.tst_name}`);
        }
        if (unit_p4_run) {
            unit_p4_run.setAttribute(
                'data-cases_ids', caseData.cases_ids);
            unit_p4_run.setAttribute(
                'data-test_function',
                `${caseData.tst_class}+${caseData.tst_name}`);
        }
        if (unit_instant_run) {
            unit_instant_run.setAttribute(
                'data-cases_ids', caseData.cases_ids);
            unit_instant_run.setAttribute(
                'data-test_function',
                `${caseData.tst_class}+${caseData.tst_name}`);
        }
    } else {
        // In case of page fails to give us test_class+test_name we just mark buttons hidden.
        if (CaseUnitModalButtons[0]) {
            CaseUnitModalButtons[0].style.display = "none";
        }
        if (TestActionsModalName[0]) {
            TestActionsModalName[0].style.display = "none";
        }
        if (SeeLogsHistory) {
            SeeLogsHistory.style.display = "none";
        }
        if (unit_wipe_run) {
            unit_wipe_run.style.display = "none";
        }
        if (unit_p4_run) {
            unit_p4_run.style.display = "none";
        }
        if (unit_instant_run) {
            unit_instant_run.style.display = "none";
        }
    }
}

/**
 * Multiple cases run selector and methods
 * Page used on: case group - user can run all cases included in actual group.
 **/

/**
 *
 * @param event
 * @returns {SQLResultSetRowList | number | HTMLCollectionOf<HTMLTableRowElement> | string | null}
 */
function tableCases(event) {
    return event.relatedTarget.parentNode.parentNode.children[2].rows;
}

/**
 * Create an key-val object with all cases got from current table.
 * @param tableRows
 * @returns {Object}
 */
function collectCasesFromRows(tableRows) {
    let casesData = new Object({
            cases_ids: [],
            casesSelectedArr: [],
        }
    );
    if (tableRows) {
        for (let row of tableRows) {
            if (row.cells['case_id']) {
                // console.log(`case_id = ${row.cells['case_id'].textContent}`);

                // Append case_id to Array, later will be used to run task with:
                casesData.cases_ids.push(row.cells['case_id'].textContent);

                // Object with selected case info:
                let caseDetails = new Object({
                    tkn_branch: '',
                    pattern_library: '',
                    pattern_folder_name: '',
                    test_py_path: '',
                    test_time_weight: '',
                });

                // Should always be!
                caseDetails.test_py_path = row.cells['test_py_path'].textContent;

                if (row.cells['tkn_branch'] && row.cells['tkn_branch'].textContent) {
                    // Means we have a usual pattern test with tkn_branch and all other info:
                    caseDetails.tkn_branch = row.cells['tkn_branch'].textContent;
                    caseDetails.pattern_library = row.cells['pattern_library'].textContent;
                    caseDetails.pattern_folder_name = row.cells['pattern_folder_name'].textContent;
                    caseDetails.test_time_weight = row.cells['test_time_weight'].textContent;
                } else {
                    console.log("Have a non-pattern test, use ID and test.py path as attributes, only")
                }
                // Append one parsed case in array of selected cases:
                casesData.casesSelectedArr.push(caseDetails);
            } else {
                // console.log("Skip row")
            }
        }
    } else {
        console.log("Skip table")
    }
    return casesData;
}

/**
 * Fill empty modal body with list of cases to run, and ids
 * @param modal
 * @param casesData
 */
function fillModalBodyWithMultipleCases(modal, casesData) {
    // let modal_variables = modal.childNodes[1].childNodes[1].childNodes[3].childNodes[3];
    let modal_variables = document.getElementById('modal-variables');
    // console.log('Modal modal-variables has children - remove them!');
    while (modal_variables.firstChild) {
        modal_variables.firstChild.remove();
    }
    // Create modal body details of case:

    for (const [keyArr, valueArr] of Object.entries(casesData)) {
        // For simple IDs array make one div:
        if (keyArr === 'cases_ids') {
            let div = document.createElement('div');
            div.setAttribute('id', keyArr);
            div.innerText = `Selected cases id list: ${valueArr}`;
            modal_variables.appendChild(div);

            // For selected cases details array create more divs
        } else if (keyArr === 'casesSelectedArr') {

            let div = document.createElement('div'); // div for all cases details below:
            div.setAttribute('id', keyArr);  // div id = casesSelectedArr
            modal_variables.appendChild(div);

            for (let caseDetails of casesData[keyArr]) {
                let caseDiv = document.createElement('div');
                // Create test py path only if no tkn_branch - that means this case is not a pattern-related.
                //TODO: Later calculate etimated time weight for all tests, by their time_weight value
                if (caseDetails.tkn_branch) {
                    caseDiv.innerText = `${caseDetails.tkn_branch}/${caseDetails.pattern_library}/${caseDetails.pattern_folder_name}\
                     t: ${caseDetails.test_time_weight}`;
                    caseDiv.setAttribute('class', 'pattern-case-details');
                    div.appendChild(caseDiv);
                } else {
                    caseDiv.innerText = `${caseDetails.test_py_path}`;
                    caseDiv.setAttribute('class', 'test-case-details');
                    div.appendChild(caseDiv);
                }

            }
        }
    }
}

/**
 * Draw buttons for multiple cases run
 * @param modal
 * @param casesData
 */
function fillButtonTestRun(modal, casesData) {
    // let modal_variables = modal.childNodes[1].childNodes[1].childNodes[3].childNodes[3];

    let test_wipe_run = document.getElementById("cases-wipe-run");
    let test_p4_run = document.getElementById("cases-p4-run");
    let test_instant_run = document.getElementById("cases-instant-run");

    test_wipe_run.setAttribute('data-cases_ids', casesData.cases_ids);
    test_wipe_run.innerText = `Run test wipe logs`;

    test_p4_run.setAttribute('data-cases_ids', casesData.cases_ids);
    test_p4_run.innerText = `Run p4, test, wipe logs`;

    test_instant_run.setAttribute('data-cases_ids', casesData.cases_ids);
    test_instant_run.innerText = `Run test instantly`;

    console.log("Buttons ready!")

}

/**
 * Simple function to activate button with Admin Operation call, show toast and run task or method.
 * @param event
 */
function buttonActivationADDM(event) {
    let btn = event.currentTarget;
    let toastBase = getToastDraft(btn.dataset);
    let toastReady = fillToastBodyWithTaskDetails(btn.dataset, toastBase);
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    RESTAdminOperationsPOST(btn.dataset, toastReady);
    showToastTask(toastReady.id); // Make toast visible
    if (btn.modalId) {
        hideModal(btn.modalId); // Hide modal
    }
}
// Later make one:
function buttonActivationUpload(event) {
    let btn = event.currentTarget;
    let toastBase = getToastDraft(btn.dataset);
    let toastReady = fillToastBodyWithTaskDetails(btn.dataset, toastBase);
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    RESTUploadOperationsPOST(btn.dataset, toastReady);
    showToastTask(toastReady.id); // Make toast visible
    if (btn.modalId) {
        hideModal(btn.modalId); // Hide modal
    }
}

/**
 * Toast actions and methods.
 * Required when user push modal buttons. Each active (not browse) button have a data-attributes inserted:
 * Listen to action 'click' grab attributes from it and proceed toast generation.
 * Send POST with test task query and GET to check if task is actually added PENDING,STARTED ot FAILURE
 **/

/**
 *
 * @return dataset from button on event
 */
function eventListenerForCaseUnitTestButtons(funcToRun) {
    // Case Unit testing:
    let unit_wipe_run = document.getElementById("unit-wipe-run");
    let unit_p4_run = document.getElementById("unit-p4-run");
    let unit_instant_run = document.getElementById("unit-instant-run");

    if (unit_wipe_run) {
        unit_wipe_run.addEventListener("click", function () {
            funcToRun(unit_wipe_run.dataset);
        });
    }
    if (unit_p4_run) {
        unit_p4_run.addEventListener("click", function () {
            funcToRun(unit_p4_run.dataset);
        });
    }
    if (unit_instant_run) {
        unit_instant_run.addEventListener("click", function () {
            funcToRun(unit_instant_run.dataset);
        });
    }
}

/**
 *
 * @return dataset from button on event
 */
function eventListenerForCaseMetaButtons(funcToRun) {
    // Listen for case meta if possible:
    let caseMeta_wipe_run = document.getElementById("wipe-run-case-meta");
    let caseMeta_p4_run = document.getElementById("p4-run-case-meta");
    let caseMeta_instant_run = document.getElementById("instant-run-case-meta");

    if (caseMeta_wipe_run) {
        caseMeta_wipe_run.addEventListener("click", function () {
            funcToRun(caseMeta_wipe_run.dataset)
        });
    }
    if (caseMeta_p4_run) {
        caseMeta_p4_run.addEventListener("click", function () {
            funcToRun(caseMeta_p4_run.dataset)
        });
    }
    if (caseMeta_instant_run) {
        caseMeta_instant_run.addEventListener("click", function () {
            funcToRun(caseMeta_instant_run.dataset)
        });
    }
}

/**
 * Listen to actions on buttons modal Run All on page /octo_tku_patterns/test_cases_group/
 * @param funcToRun
 */
function eventListenerForCaseGroupButtons(funcToRun) {
    // Listen for case meta if possible:
    let casesGroupWipeRun = document.getElementById("cases-wipe-run");
    let casesGroupP4Run = document.getElementById("cases-p4-run");
    let casesGroupInstantRun = document.getElementById("cases-instant-run");

    if (casesGroupWipeRun) {
        casesGroupWipeRun.addEventListener("click", function () {
            funcToRun(casesGroupWipeRun.dataset)
        });
    }
    if (casesGroupP4Run) {
        casesGroupP4Run.addEventListener("click", function () {
            funcToRun(casesGroupP4Run.dataset)
        });
    }
    if (casesGroupInstantRun) {
        casesGroupInstantRun.addEventListener("click", function () {
            funcToRun(casesGroupInstantRun.dataset)
        });
    }
}

/**
 * Making a copy of toast draft HTML and assign new copy with unique case ID
 * @returns {Node}
 */
function getToastDraftMultipleCases() {
    let toastDraft = document.getElementById('toastDraft'); // Get draft toast from page foot
    let toastBase = toastDraft.children[0].cloneNode(true);  // Toast object
    // Set toast values:
    toastBase.setAttribute('data-delay', 30000); // 30 sec. Wait to task mod
    // Make a toast with stale ID, there is a group execution, we don't need multiple toasts
    toastBase.id = 'multiple-cases-run-toast';
    return toastBase
}

function getToastDraft(btnDataSet) {
    let toastDraft = document.getElementById('toastDraft'); // Get draft toast from page foot
    let toastBase = toastDraft.children[0].cloneNode(true);  // Toast object
    toastBase.setAttribute('data-delay', 30000); // 30 sec. Wait to task mod
    // Assign new toast copy a value ID based on item ID (case id or case unique attrs)

    if (btnDataSet.addm_group) {
        toastBase.id = `${btnDataSet.operation_key}-${btnDataSet.addm_group}`;

    } else if (btnDataSet.addm_host && btnDataSet.command_key) {
        toastBase.id = `${btnDataSet.addm_host}-${btnDataSet.command_key}`;

    } else if (btnDataSet.addm_host && btnDataSet.operation_key) {
        toastBase.id = `${btnDataSet.addm_host}-${btnDataSet.operation_key}`;

    } else if (btnDataSet.addm_group && btnDataSet.command_key) {
        toastBase.id = `${btnDataSet.addm_group}-${btnDataSet.command_key}`;

    } else {
        toastBase.id = `${btnDataSet.operation_key}`;
    }
    return toastBase
}

function fillToastBodyWithTaskDetails(btnDataSet, toastBase) {
    let div = document.createElement('div');  // toast-body
    div.setAttribute('id', 'taskOperationType');
    // Simply show JSON of button data
    if (btnDataSet.operation_key) {
        div.innerText = `Adding: ${JSON.stringify(btnDataSet)}`;
        div.style.wordWrap = 'break-word';
        toastBase.childNodes[3].appendChild(div);
    }
    return toastBase
}

function toastModifyOtherTasksPre(toastReady, tasksSet, message) {
    let div = document.createElement('div');  // toast-body
    div.setAttribute('id', 'task_id');
    if (tasksSet) {
        div.innerText = `task: ${JSON.stringify(tasksSet)}`;
    } else {
        div.innerText = `${message}`;
    }
    toastReady.childNodes[3].appendChild(div);
}

/**
 * Already published toast now modifying with new data: when task has been added and GET request return it's data
 * NOTE: It does not work while task is processing. Only when finished and saved to DB
 * @param toastId
 * @param taskObj
 */
function toastModifySuccess(taskObj, toastId) {
    let toastPublished = document.getElementById(toastId);
    let task_status = document.createElement('div');  // toast-body
    task_status.setAttribute('id', 'task_status');
    // console.log("Modifying toast with task:");
    // console.table(caseFullData);
    if (taskObj.state) {
        task_status.innerText = `task: ${taskObj.status} - ${taskObj.state}`;
    } else {
        if (taskObj.status === 'FAILURE') {
            task_status.innerText = `task: ${taskObj.status} - please check!`;
        } else {
            task_status.innerText = `task: ${taskObj.status} - wait in queue...`;
        }
    }
    toastPublished.childNodes[3].appendChild(task_status);
}

function toastModifyOtherTaskSuccess(toastReady, task) {
    let task_status = document.createElement('div');  // toast-body
    task_status.setAttribute('id', 'task_status');
    if (task.state) {
        task_status.innerText = `task: ${task.status} - ${task.state}`;
    } else {
        if (task.status === 'FAILURE') {
            task_status.innerText = `task: ${task.status} - please check!`;
        } else if (task.status) {
            task_status.innerText = `task: ${task.status} - wait in queue...`;
        } else if (task) {
            task_status.innerText = `${JSON.stringify(task)}`;
        }
    }
    toastReady.childNodes[3].appendChild(task_status);
}

/**
 * TODO: Remove!
 * Make toast show and modal object hide.
 * @param toastID
 */
function showToast(toastID) {
    $('#actionsModal').modal('hide');
    $('#' + toastID).toast('show')
}

function showToastTask(toastID) {
    $('#' + toastID).toast('show');
}

function hideModal(modalID) {
    $('#' + modalID).modal('hide');
}

function showToastHideModal(toastID) {
    // $('#' + modalID).modal('hide');
    $('#' + toastID).toast('show')
}

/**
 * REST
 **/

function waitResultTask(toastReady, taskID) {
    setTimeout(function () {
        if (typeof taskID === 'object') {
            for (const [key, task_id] of Object.entries(taskID)) {
                console.log(`Getting tasks statuses: ${key} ${task_id}`);
                new RESTGetTaskGeneric(toastReady, task_id);
            }
        } else if (typeof taskID === 'string') {
            new RESTGetTaskGeneric(toastReady, taskID);
        }
    }, 15000);
}

/**
 * REST GET request to obtain task status and data by task_id.
 * If request is 'success' - try to modify published toast with same ID as case(or test) to show current task status
 * @param taskID
 * @param toastId
 * @constructor
 */
function RESTGetTask(taskID, toastId) {
    // console.log(`GET user test task by id: ${testButtonDataset.task_id}`);
    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/octo_tku_patterns/user_test_add/",
        data: {task_id: taskID},
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            // console.log(`GET result: ${result}`);
            // console.table(result[0]);
            let task = result[0];
            if (task && task.status) {
                // console.log("caseFullData right after GET");
                // console.table(caseFullData);
                // On success - run toast modify:
                toastModifySuccess(task, toastId);
            } else {
                console.log("Task GET failed, no task found or no status");
            }
        },
        "error": function () {
            console.log("GET TASK ERROR, something goes wrong...");
        },
    });
}

/**
 * http://127.0.0.1:8000/octo_admin/task_operation/?operation_key=get_task_status_by_id
 * @param toastReady
 * @param taskID
 * @constructor
 */
function RESTGetTaskGeneric(toastReady, taskID) {
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/x-www-form-urlencoded",
        url: "/octo_admin/task_operation/",
        data: {operation_key: 'get_task_status_by_id', task_id: taskID},
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            console.log(result);
            let task = result.response;
            if (task && task.status) {
                toastModifyOtherTaskSuccess(toastReady, task);
            }
            else if (task) {
                // May return an array when task was finished and added to DB already:
                toastModifyOtherTaskSuccess(toastReady, task);
            } else {
                toastModifyOtherTaskSuccess(toastReady, task);
                console.log("Task GET failed, no task found or no status");
            }
        },
        "error": function () {
            toastModifyOtherTaskSuccess(toastReady, "GET TASK ERROR, something goes wrong...");
            console.log("GET TASK ERROR, something goes wrong...");
        },
    });
}

/**
 * Get case details on test digest pages of deeper level: test items, test history.
 * Main important action - this function gets case ID which later used for test run.
 * This approach is much better then pass pattern_lib, folder, branch and so on.
 * @param caseData
 * @param modal
 * @param event
 * @param callThen
 * @constructor
 */
function RESTGetCaseByTestPyPath(caseData, modal, event, callThen) {
    // console.log(`GET user test task by id: ${testButtonDataset.task_id}`);
    let caseItem = {};
    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/api/v1/cases/octo_test_cases/",
        data: {test_py_path: caseData.test_py_path},
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            let caseItem = result.results[0];
            if (caseItem && caseItem.id) {
                callThen(caseItem, caseData, modal, event);
            } else {
                console.log("Get Case failed: " + data);
            }
        },
        "error": function () {
            console.log("GET Case ERROR, something goes wrong...");
        },
    });
    return caseItem;
}

/**
 * Inspect workers with short version.
 * @param workerList
 * @param tasksBody
 * @param createWorkerRow
 * @returns {Array}
 * @constructor
 */
function RESTGetCeleryWorkersQueues(workerList, tasksBody, createWorkerRow) {
    let data = {};
    if (tasksBody) {
        data.task_body = '1';
    }
    if (workerList) {
        data.workers_list = workerList;
    }

    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/inspect_workers_short/",
        data: data,
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            // console.log(`GET result: ${result}`);
            // console.table(result);
            if (result) {
                createWorkerRow(result)
            } else {
                console.log("Task GET failed, no task found or no status");
            }
        },
        "error": function () {
            console.log("GET TASK ERROR, something goes wrong...");
        },
    });
    return [];
}

/**
 * Post admin task for addm operations.
 * Show toast with selected task, addm name ot group and operation key and args
 * Later get task id, wait, show toast task response.
 * @param btnDataset
 * @param toastReady
 * @returns {*}
 */
function RESTAdminOperationsPOST(btnDataset, toastReady) {
    console.log(btnDataset);
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/x-www-form-urlencoded",
        url: "/octo_admin/admin_operations/",
        data: btnDataset,
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            console.log(`POST result: ${result}`);
            if (result) {
                console.table(result);
                toastModifyOtherTasksPre(toastReady, result.task_id);
                waitResultTask(toastReady, result.task_id);
            } else {
                console.log("Task POST send, but haven't been added. No task_id in result!");
                toastModifyOtherTasksPre(toastReady, undefined,
                    "Task POST send, but haven't been added. No task_id in result!");
            }
        },
        "error": function () {
            console.log("POST TASK ERROR, something goes wrong...");
            toastModifyOtherTasksPre(toastReady, undefined,
                "POST TASK ERROR, something goes wrong...");
        },
    });
    return btnDataset;
}

// Later make universal:
function RESTUploadOperationsPOST(btnDataset, toastReady) {
    console.log(btnDataset);
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/x-www-form-urlencoded",
        url: "/octo_tku_upload/tku_operations/",
        data: btnDataset,
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            console.log(`POST result: ${result}`);
            if (result) {
                console.table(result);
                toastModifyOtherTasksPre(toastReady, result.task_id);
                waitResultTask(toastReady, result.task_id);
            } else {
                console.log("Task POST send, but haven't been added. No task_id in result!");
                toastModifyOtherTasksPre(toastReady, undefined,
                    "Task POST send, but haven't been added. No task_id in result!");
            }
        },
        "error": function () {
            console.log("POST TASK ERROR, something goes wrong...");
            toastModifyOtherTasksPre(toastReady, undefined,
                "POST TASK ERROR, something goes wrong...");
        },
    });
    return btnDataset;
}