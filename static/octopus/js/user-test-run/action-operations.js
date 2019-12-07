/**
 * MODAL OPERATIONS:
 */

function getButtonFromEvent(event) {
    return $(event.relatedTarget); // Button that triggered the modal
}

/**
 *
 * @param dataJSON
 * @param case_id
 * @returns {[]}
 */
function makeCaseTestDataSet(dataJSON, case_id) {
    let caseTestDataset = [];
        for (let testItem of dataJSON) {
            //For case on last test
            if (parseInt(testItem['case_id']) === parseInt(case_id)) {
                // console.log(testItem);
                caseTestDataset.push(testItem);

            // For test on test details tables
            } else if (parseInt(testItem['id']) === parseInt(case_id)) {
                caseTestDataset.push(testItem);
            }
        }
    return caseTestDataset
}

function fillModalBodyNew(modal, testItemsJSON, caseAttrs) {
    // Create in modal body:
    let modal_variables = document.getElementById('modal-variables');
    // Remove extra children if any found. Could be leftovers from previous modal draw!
    while (modal_variables.firstChild) {
        modal_variables.firstChild.remove();
    }
    // Make modal body block with case details from arr below:
    if (testItemsJSON && testItemsJSON[0]) {
        let firstItem =testItemsJSON[0];
        for (let attrK of caseAttrs) {
            let div = document.createElement('div');
            div.setAttribute('id', attrK);
            div.innerText = firstItem[attrK];
            modal_variables.appendChild(div);
        }
    }
}

function fillModalBodyTableTestFails(testItemsJSON) {
    let modal_variables = document.getElementById('modal-variables');
    // Make table sum of one testcase test counters
    let tr = document.createElement('tr');
    let colNames = ['addm_name', 'fails', 'error', 'passed', 'skipped'];
    for (let name of colNames) {
        let td = document.createElement('td');
        td.innerText = name;
        tr.appendChild(td);
    }
    modal_variables.appendChild(tr);

    // Fill modal body > modal variables with testItemsJSON attributes:
    for (let testItem of testItemsJSON) {
        if (testItem) {

            // Create table:
            let tr = document.createElement('tr');
            tr.setAttribute('id', testItem['addm_name']);
            for (let key in testItem) {
                if (testItem.hasOwnProperty(key) && colNames.includes(key)) {
                    let td = document.createElement('td');
                    td.setAttribute('class', key);
                    td.innerText = testItem[key];
                    tr.appendChild(td);
                }
            }
            modal_variables.appendChild(tr);
        }
    }

}

function detectADDMSelectorFromContext(button, caseData) {
    let addm_name_url = '';
    // Add addm_name attribute for sort OR to activate tab
    if (button.data('addm_name') && button.data('addm_name') !== 'None') {
        addm_name_url = `;addm_name=${button.data('addm_name')}`;
    } else {
        if (caseData && caseData.addm_name) {
            // Yes, there is no addm_name in context, but we activate JS-able tab in next page
            addm_name_url = `#${caseData.addm_name}`;
        }
    }
    return addm_name_url
}

function detectTestStatusSelectorFromContext(button, caseData) {
    let tst_status = button.data('tst_status');
    let tst_status_url = '';
    if (tst_status) {
        tst_status_url = `;tst_status=${tst_status}`;
    }
    return tst_status_url
}

function composeLogsHyperlinksNew(caseDataJSON, addm_name_url, tst_status_url) {
    let caseData = caseDataJSON[0];
    let seeLogs = document.getElementById('see-logs');
    if (seeLogs) {
        if (caseData['tkn_branch']) {
            // For when we have a usual pattern related case
            seeLogs.href = `/octo_tku_patterns/test_details/?tkn_branch=${
                caseData['tkn_branch']};pattern_library=${
                caseData['pattern_library']};pattern_folder_name=${
                caseData['pattern_folder_name']}${tst_status_url}${addm_name_url}`;
        } else {
            // For when we have a main or octo test:
            seeLogs.href = `/octo_tku_patterns/test_details/?test_py_path=${
                caseData['test_py_path']}${tst_status_url}${addm_name_url}`;
        }
    } else {
        // console.log("Cannot find element id for seeLogs " + seeLogs)
    }

    let seeLogsHist = document.getElementById('see-logs-history');
    if (seeLogsHist) {
        if (caseData['tkn_branch']) {
            // For when we have a usual pattern related case
            if (caseData['tst_class'] && caseData['tst_name']) {
                seeLogsHist.href = `/octo_tku_patterns/test_item_history/?tkn_branch=${
                    caseData['tkn_branch']};pattern_library=${
                    caseData['pattern_library']};pattern_folder_name=${
                    caseData['pattern_folder_name']};tst_class=${
                    caseData['tst_class']};tst_name=${
                    caseData['tst_name']}${tst_status_url}${addm_name_url}`;
            } else {
                seeLogsHist.href = `/octo_tku_patterns/test_item_history/?tkn_branch=${
                    caseData['tkn_branch']};pattern_library=${
                    caseData['pattern_library']};pattern_folder_name=${
                    caseData['pattern_folder_name']}${tst_status_url}${addm_name_url}`;
            }
        } else {
            // For when we have a main or octo test:
            if (caseData['tst_class'] && caseData['tst_name']) {
                seeLogsHist.href = `/octo_tku_patterns/test_item_history/?test_py_path=${
                    caseData['test_py_path']};tst_class=${
                    caseData['tst_class']};tst_name=${
                    caseData['tst_name']}${tst_status_url}${addm_name_url}`;
            } else {
                seeLogsHist.href = `/octo_tku_patterns/test_item_history/?test_py_path=${
                    caseData['test_py_path']}${tst_status_url}${addm_name_url}`;
            }
        }
    } else {
        // console.log("Cannot find element id for seeLogsHist " + seeLogsHist)
    }
}

function composeCaseHyperlinksNew(caseDataJSON) {
    let caseData = caseDataJSON[0];
    let seeCaseInfo = document.getElementById('all-info');
    if (seeCaseInfo) {
        seeCaseInfo.href = `/octo_tku_patterns/test_case/${caseData['case_id']}`;
    } else {
        // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
    }
    let editCase = document.getElementById('edit-case');
    if (editCase) {
        editCase.href = `/octo_tku_patterns/test_case/change/${caseData['case_id']}`;
    } else {
        // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
    }
}

function assignTestCaseTestButtonsNew(caseDataJSON) {
    let caseData = caseDataJSON[0];
    let test_wipe_run = document.getElementById(
        "wipe-run");
    if (test_wipe_run) {
        test_wipe_run.setAttribute(
            'data-case_id', caseData['case_id']);
    }
    let test_p4_run = document.getElementById(
        "p4-run");
    if (test_p4_run) {
        test_p4_run.setAttribute(
            'data-case_id', caseData['case_id']);
    }
    let test_instant_run = document.getElementById(
        "instant-run");
    if (test_instant_run) {
        test_instant_run.setAttribute(
            'data-case_id', caseData['case_id']);
    }
}

/**
 * TOAST OPERATIONS:
 */

function eventListenerForCaseTestButtons(funcToRun) {
    // Test case testing
    let test_wipe_run = document.getElementById("wipe-run");
    let test_p4_run = document.getElementById("p4-run");
    let test_instant_run = document.getElementById("instant-run");

    // Clear buttons dataset from any extra options:
    let testButtonUseKeys = ['wipe', 'refresh', 'test_mode'];
    let testButtonDataset = new Object({
        'test_mode': ''
    });

    if (test_wipe_run) {
        test_wipe_run.addEventListener("click", function () {
            // console.log("test_wipe_run click");
            for (let [key, value] of Object.entries(test_wipe_run.dataset)) {
                if (testButtonUseKeys.includes(key)) {
                    testButtonDataset[key] = value;
                }
            }
            funcToRun(testButtonDataset);
        });
    }
    if (test_p4_run) {
        test_p4_run.addEventListener("click", function () {
            // console.log("test_p4_run click");
            for (let [key, value] of Object.entries(test_p4_run.dataset)) {
                if (testButtonUseKeys.includes(key)) {
                    testButtonDataset[key] = value;
                }
            }
            funcToRun(testButtonDataset);
        });
    }
    if (test_instant_run) {
        test_instant_run.addEventListener("click", function () {
            // console.log("test_instant_run click");
            for (let [key, value] of Object.entries(test_instant_run.dataset)) {
                if (testButtonUseKeys.includes(key)) {
                    testButtonDataset[key] = value;
                }
            }
            funcToRun(testButtonDataset);
        });
    }
}

function getToastDraftWithId(caseData) {
    let toastDraft = document.getElementById('toastDraft'); // Get draft toast from page foot
    let toastBase = toastDraft.children[0].cloneNode(true);  // Toast object

    // Set toast values:
    toastBase.setAttribute('data-delay', 30000); // 30 sec. Wait to task mod
    // Assign new toast copy a value ID based on item ID (case id or case unique attrs)
    if (caseData['case_id']) {
        toastBase.id = caseData['case_id'];
    } else if (caseData['cases_ids']) {
        toastBase.id = caseData['cases_ids'];
    } else if (caseData['test_id']) {
        toastBase.id = caseData['test_id'];
    } else {
        toastBase.id = `${caseData['tkn_branch']}_${caseData['pattern_library']}_${caseData['pattern_folder_name']}`;
    }

    // Toast elements:
    // toastBase.childNodes[1];  // toast-header
    // toastBase.childNodes[3];  // toast-body
    return toastBase
}

function fillToastBodyWithTestAttributes(toastBase, caseData, testButtonDataset) {
    let toastBody = toastBase.childNodes[3];  // Path to toast body.
    let testDetails = document.createElement('div');
    let testMode = document.createElement('div');

    testDetails.setAttribute('id', testButtonDataset.test_mode);
    testMode.setAttribute('id', 'test_mode');

    // Depend on data-test_mode="" attribute fill toast with caseData details:
    if (testButtonDataset.test_mode === 'test_by_id') {
        testDetails.innerText = 'Will run test by case id';
        let tknBranchPattLib = document.createElement('div');
        let patternDirectory = document.createElement('div');
        tknBranchPattLib.setAttribute('id', 'tknBranchPattLib');
        patternDirectory.setAttribute('id', 'patternDirectory');
        tknBranchPattLib.innerText = caseData['pattern_library'];
        patternDirectory.innerText = caseData['pattern_folder_name'];
        toastBody.appendChild(tknBranchPattLib);
        toastBody.appendChild(patternDirectory);
        // Add extra div with the name of test method if it was found in test button dataset or case Data
        if (caseData['test_function'] && testButtonDataset.test_function) {
            let test_function = document.createElement('div');
            test_function.setAttribute('id', 'testUnitFunction');
            if (caseData['test_function']) {
                test_function.innerText = caseData['test_function'];
            } else if (testButtonDataset.test_function) {
                test_function.innerText = caseData['test_function'];
            }
            toastBase.childNodes[3].appendChild(test_function);
        }

    } else if (testButtonDataset.test_mode === 'test_by_change') {
        testDetails.innerText = 'Will run all tests by cases change';
        let testMetadataAttrs = document.createElement('div');
        testMetadataAttrs.setAttribute('id', caseData['change']);

    } else if (testButtonDataset.test_mode === 'test_by_user') {
        testDetails.innerText = 'Will run all test by cases user';
        let testMetadataAttrs = document.createElement('div');
        testMetadataAttrs.setAttribute('id', caseData['change_user']);

    } else if (testButtonDataset.test_mode === 'test_by_change_ticket') {
        testDetails.innerText = 'Will run all tests by cases ticket';
        let testMetadataAttrs = document.createElement('div');
        testMetadataAttrs.setAttribute('id', caseData['change_ticket']);

    } else if (testButtonDataset.test_mode === 'test_by_change_review') {
        testDetails.innerText = 'Will run all tests test by cases review';
        let testMetadataAttrs = document.createElement('div');
        testMetadataAttrs.setAttribute('id', caseData['change_review']);

    } else if (testButtonDataset.test_mode === 'test_by_multiple_ids') {
        testDetails.innerText = 'Will run multiple cases by selected ids';
        let testMetadataAttrs = document.createElement('div');
        testMetadataAttrs.setAttribute('id', caseData['case_id']);

    } else {
        testDetails.innerText = 'Will run test in other mode. Not yet implemented?'
    }
    // Add case and test details to toast body:
    toastBody.append(testDetails);

    if (testButtonDataset.wipe) {
        testMode.innerText = `Wipe latest logs`;
        toastBase.childNodes[3].appendChild(testMode);
    } else if (testButtonDataset.refresh) {
        testMode.innerText = `Run p4 sync, wipe latest logs`;
        toastBase.childNodes[3].appendChild(testMode);
    } else {
        testMode.innerText = `Instant run, keep logs, no p4 sync`;
        toastBase.childNodes[3].appendChild(testMode);
    }

    return toastBase
}

function appendToastToStack(toastReady) {
    // Append new toast to toast stack container:
    document.getElementById('toastStack').appendChild(toastReady);
}

function composeTestDataSet(caseData, testButtonDataset) {
    if (testButtonDataset.test_mode === 'test_by_id') {
        // Request selector use cases_ids for single and multiple cases anyway:
        testButtonDataset.cases_ids = caseData['case_id'];
    } else if (testButtonDataset.test_mode === 'test_by_change') {
        testButtonDataset.change = caseData['change'];
    } else if (testButtonDataset.test_mode === 'test_by_user') {
        testButtonDataset.change_user = caseData['change_user'];
    } else if (testButtonDataset.test_mode === 'test_by_change_ticket') {
        testButtonDataset.change_ticket = caseData['change_ticket'];
    } else if (testButtonDataset.test_mode === 'test_by_change_review') {
        testButtonDataset.change_review = caseData['change_review'];
    } else if (testButtonDataset.test_mode === 'test_by_multiple_ids') {
        testButtonDataset.cases_ids = caseData['cases_ids'];
    } else {
    }
}

/**
 * REST OPERATIONS:
 */

function RESTPostTask(testButtonDataset, toastBase) {
    console.log(`POST user test: `);
    console.log(testButtonDataset);
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/x-www-form-urlencoded",
        url: "/octo_tku_patterns/user_test_add/",
        data: testButtonDataset,
        "beforeSend": function (xhr, settings) {
            $.ajaxSettings.beforeSend(xhr, settings)
        },
        "success": function (result) {
            // console.log(`POST result: ${result}`);
            if (result.task_id) {
                // console.log("testButtonDataset after POST: ");
                // console.table(testButtonDataset);
                // On success - run get task status:
                toastModifyCaseDataPre(result.task_id, toastBase.id);
                waitResult(result.task_id, toastBase.id);
            } else {
                console.log("Task POST send, but haven't been added. No task_id in result!")
            }
        },
        "error": function () {
            console.log("POST TASK ERROR, something goes wrong...")
        },
    });
}

/**
 * Get case details on test digest pages of deeper level: test items, test history.
 * Main important action - this function gets case ID which later used for test run.
 * This approach is much better then pass pattern_lib, folder, branch and so on.
 * @param caseData
 * @param callThen
 * @constructor
 */
function RESTGetCaseByTestPyPath(caseData, callThen) {
    // console.log(`GET user test task by id: ${testButtonDataset.task_id}`);
    let caseItem = {};
    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/api/v1/cases/octo_test_cases/",
        data: {test_py_path: caseData['test_py_path']},
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            let caseItem = result.results[0];
            if (caseItem && caseItem.id) {
                console.log(caseItem);
                callThen();
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
 * AFTER REST OPERATIONS:
 */

function toastModifyCaseDataPre(taskId, toastId) {
    let toastPublished = document.getElementById(toastId);
    let toastBody = toastPublished.childNodes[3];  // Path to toast body.
    let taskIdDiv = document.createElement('div');  // toast-body
    taskIdDiv.setAttribute('id', 'task_id');
    taskIdDiv.innerText = `task: ${taskId}`;
    toastBody.appendChild(taskIdDiv);
}

function waitResult(taskID, toastId) {
    setTimeout(function () {
        new RESTGetTask(taskID, toastId);
    }, 5000);
}

function RESTGetTask(taskID, toastId) {
    // console.log(`GET user test task by id: ${testButtonDataset.task_id}`);
    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/octo_tku_patterns/user_test_add/",
        data: {task_id: taskID},
        "beforeSend": function (xhr, settings) {
            $.ajaxSettings.beforeSend(xhr, settings)
        },
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