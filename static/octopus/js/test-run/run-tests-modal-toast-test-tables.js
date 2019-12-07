// let caseData = new Object({
//     addm_name: null,
// });
// let excludeIds = [
//     'addm_v_int',
//     'test_items_prepared',
//     'fails', 'error', 'passed', 'skipped',
//     'action', 'actions', 'test_type', 'test_case_depot_path'
// ];
//
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal
//  * Returns table row dependent from this row's pushed button of modal or so.
//  * Works for tables in test digests, ...
//  * @param event
//  * @returns {Node & ParentNode}
//  */
// function getTableRowFromEvent(event) {
//     return event.relatedTarget.parentNode.parentNode;
// }
//
// /**
//  * * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal
//  * Return actual button which cause an event.
//  * @param event
//  * @returns {jQuery.fn.init|jQuery|HTMLElement}
//  */
// function getButtonFromEvent(event) {
//     return $(event.relatedTarget); // Button that triggered the modal
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal
//  * Collect all cells data from related table row - make dataSet
//  * @param tableRow
//  * @returns {Object}
//  */
// function parseTableRowForCaseData(tableRow) {
//     // Create new empty case Data dict - later fill with cell values and ids as keys
//     let excludeKeys = ['actions', 'action'];
//     for (let [key, value] of Object.entries(tableRow.cells)) {
//         if (value && value.id && value.textContent) {
//             if (excludeKeys.includes(value.id)) {
//                 // console.log("Exclude id: "+ value.id)
//             } else {
//                 // console.log(`${value.id}: '${value.textContent}'`);
//                 caseData[value.id] = value.textContent.split(' ').join('');
//             }
//         } else {
//             // console.log(`Value is empty for id: ${value.id}`)
//         }
//     }
//     return caseData
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal
//  * Insert some parsed data of caseData in modal body
//  * @param modal
//  * @param caseData
//  * @param excludeIds arr with Id keys to not display on modal variables
//  */
// function fillModalBody(modal, caseData, excludeIds) {
//     // Create in modal body:
//     // let modal_variables = modal.childNodes[1].childNodes[1].childNodes[3].childNodes[3];
//     let modal_variables = document.getElementById('modal-variables');
//     // Remove extra children if any found. Could be leftovers from previous modal draw!
//     while (modal_variables.firstChild) {
//         modal_variables.firstChild.remove();
//     }
//     // Fill modal body > modal variables with caseData attributes:
//     for (const [key, value] of Object.entries(caseData)) {
//         // console.log("Creating modal divs:" + key, value);
//         if (value && !excludeIds.includes(key)) {
//             let div = document.createElement('div');
//             div.setAttribute('id', key);
//             // div.text(value);
//             // div.innerText = `${key}: ${value}`;
//             div.innerText = `${value}`;
//             modal_variables.appendChild(div);
//         }
//     }
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal
//  * Make buttons for test run have required attributes to run test:
//  * Single test.py modes: wipe-run, p4-run, instant-run
//  * @param caseData
//  */
// function assignTestCaseTestButtons(caseData) {
//     let test_wipe_run = document.getElementById(
//         "wipe-run");
//     if (test_wipe_run) {
//         test_wipe_run.setAttribute(
//             'data-case_id', caseData.case_id);
//     }
//     let test_p4_run = document.getElementById(
//         "p4-run");
//     if (test_p4_run) {
//         test_p4_run.setAttribute(
//             'data-case_id', caseData.case_id);
//     }
//     let test_instant_run = document.getElementById(
//         "instant-run");
//     if (test_instant_run) {
//         test_instant_run.setAttribute(
//             'data-case_id', caseData.case_id);
//     }
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal
//  * Make href for logs and history
//  * @param caseData
//  * @param addm_name_url
//  * @param tst_status_url
//  */
// function composeLogsHyperlinks(caseData, addm_name_url, tst_status_url) {
//
//     let seeLogs = document.getElementById('see-logs');
//     if (seeLogs) {
//         if (caseData.tkn_branch) {
//             // For when we have a usual pattern related case
//             seeLogs.href = `/octo_tku_patterns/test_details/?tkn_branch=${caseData.tkn_branch};pattern_library=${caseData.pattern_library};pattern_folder_name=${caseData.pattern_folder_name}${tst_status_url}${addm_name_url}`;
//         } else {
//             // For when we have a main or octo test:
//             seeLogs.href = `/octo_tku_patterns/test_details/?test_py_path=${caseData.test_py_path}${tst_status_url}${addm_name_url}`;
//         }
//     } else {
//         // console.log("Cannot find element id for seeLogs " + seeLogs)
//     }
//
//     let seeLogsHist = document.getElementById('see-logs-history');
//     if (seeLogsHist) {
//         if (caseData.tkn_branch) {
//             // For when we have a usual pattern related case
//             if (caseData.tst_class && caseData.tst_name) {
//                 seeLogsHist.href = `/octo_tku_patterns/test_item_history/?tkn_branch=${caseData.tkn_branch};pattern_library=${caseData.pattern_library};pattern_folder_name=${caseData.pattern_folder_name};tst_class=${caseData.tst_class};tst_name=${caseData.tst_name}${tst_status_url}${addm_name_url}`;
//             } else {
//                 seeLogsHist.href = `/octo_tku_patterns/test_item_history/?tkn_branch=${caseData.tkn_branch};pattern_library=${caseData.pattern_library};pattern_folder_name=${caseData.pattern_folder_name}${tst_status_url}${addm_name_url}`;
//             }
//         } else {
//             // For when we have a main or octo test:
//             if (caseData.tst_class && caseData.tst_name) {
//                 seeLogsHist.href = `/octo_tku_patterns/test_item_history/?test_py_path=${caseData.test_py_path};tst_class=${caseData.tst_class};tst_name=${caseData.tst_name}${tst_status_url}${addm_name_url}`;
//             } else {
//                 seeLogsHist.href = `/octo_tku_patterns/test_item_history/?test_py_path=${caseData.test_py_path}${tst_status_url}${addm_name_url}`;
//             }
//         }
//     } else {
//         // console.log("Cannot find element id for seeLogsHist " + seeLogsHist)
//     }
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal
//  * Make links for case: edit, view, etc.
//  * @param caseData
//  */
// function composeCaseHyperlinks(caseData) {
//     let seeCaseInfo = document.getElementById('all-info');
//     if (seeCaseInfo) {
//         seeCaseInfo.href = `/octo_tku_patterns/test_case/${caseData.case_id}`;
//     } else {
//         // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
//     }
//     let editCase = document.getElementById('edit-case');
//     if (editCase) {
//         editCase.href = `/octo_tku_patterns/test_case/change/${caseData.case_id}`;
//     } else {
//         // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
//     }
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal, testToast
//  * Making a copy of toast draft HTML and assign new copy with unique case ID
//  * @param caseData
//  * @returns {Node}
//  */
// function getToastDraftWithId(caseData) {
//     let toastDraft = document.getElementById('toastDraft'); // Get draft toast from page foot
//     let toastBase = toastDraft.children[0].cloneNode(true);  // Toast object
//
//     // Set toast values:
//     toastBase.setAttribute('data-delay', 30000); // 30 sec. Wait to task mod
//     // Assign new toast copy a value ID based on item ID (case id or case unique attrs)
//     if (caseData.case_id) {
//         toastBase.id = caseData.case_id;
//     } else if (caseData.cases_ids) {
//         toastBase.id = caseData.cases_ids;
//     } else if (caseData.test_id) {
//         toastBase.id = caseData.test_id;
//     } else {
//         toastBase.id = `${caseData.tkn_branch}_${caseData.pattern_library}_${caseData.pattern_folder_name}`;
//     }
//
//     // Toast elements:
//     // toastBase.childNodes[1];  // toast-header
//     // toastBase.childNodes[3];  // toast-body
//     return toastBase
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal, testToast
//  * Fill new toast copy body with attributes from case to show which test has been started and what pattern.
//  * @param toastBase
//  * @param caseData
//  * @param testButtonDataset
//  * @returns {*}
//  */
//
// let fillToastBodyWithTestAttributes_ = new Object({
//     fillModalTestModeById: function (toastBase, caseData, testButtonDataset) {
//         let toastBody = toastBase.childNodes[3];  // Path to toast body.
//         let testDetails = document.createElement('div');
//         let testMode = document.createElement('div');
//
//         testDetails.setAttribute('id', testButtonDataset.test_mode);
//         testMode.setAttribute('id', 'test_mode');
//         // Depend on data-test_mode="" attribute fill toast with caseData details:
//         if (testButtonDataset.test_mode === 'test_by_id') {
//             testDetails.innerText = 'Will run test by case id';
//             let tknBranchPattLib = document.createElement('div');
//             let patternDirectory = document.createElement('div');
//             tknBranchPattLib.setAttribute('id', 'tknBranchPattLib');
//             patternDirectory.setAttribute('id', 'patternDirectory');
//             tknBranchPattLib.innerText = caseData.pattern_library;
//             patternDirectory.innerText = caseData.pattern_folder_name;
//             toastBody.appendChild(tknBranchPattLib);
//             toastBody.appendChild(patternDirectory);
//             // Add extra div with the name of test method if it was found in test button dataset or caseData
//             if (caseData.test_function && testButtonDataset.test_function) {
//                 let test_function = document.createElement('div');
//                 test_function.setAttribute('id', 'testUnitFunction');
//                 if (caseData.test_function) {
//                     test_function.innerText = caseData.test_function;
//                 } else if (testButtonDataset.test_function) {
//                     test_function.innerText = caseData.test_function;
//                 }
//                 toastBase.childNodes[3].appendChild(test_function);
//             }
//         }
//         // Add case and test details to toast body:
//         toastBody.append(testDetails);
//
//         if (testButtonDataset.wipe) {
//             testMode.innerText = `Wipe latest logs`;
//             toastBase.childNodes[3].appendChild(testMode);
//         } else if (testButtonDataset.refresh) {
//             testMode.innerText = `Run p4 sync, wipe latest logs`;
//             toastBase.childNodes[3].appendChild(testMode);
//         } else {
//             testMode.innerText = `Instant run, keep logs, no p4 sync`;
//             toastBase.childNodes[3].appendChild(testMode);
//         }
//
//         return toastBase
//
//     }
// });
//
// function fillToastBodyWithTestAttributes(toastBase, caseData, testButtonDataset) {
//     let toastBody = toastBase.childNodes[3];  // Path to toast body.
//     let testDetails = document.createElement('div');
//     let testMode = document.createElement('div');
//
//     testDetails.setAttribute('id', testButtonDataset.test_mode);
//     testMode.setAttribute('id', 'test_mode');
//
//     // Depend on data-test_mode="" attribute fill toast with caseData details:
//     if (testButtonDataset.test_mode === 'test_by_id') {
//         testDetails.innerText = 'Will run test by case id';
//         let tknBranchPattLib = document.createElement('div');
//         let patternDirectory = document.createElement('div');
//         tknBranchPattLib.setAttribute('id', 'tknBranchPattLib');
//         patternDirectory.setAttribute('id', 'patternDirectory');
//         tknBranchPattLib.innerText = caseData.pattern_library;
//         patternDirectory.innerText = caseData.pattern_folder_name;
//         toastBody.appendChild(tknBranchPattLib);
//         toastBody.appendChild(patternDirectory);
//         // Add extra div with the name of test method if it was found in test button dataset or caseData
//         if (caseData.test_function && testButtonDataset.test_function) {
//             let test_function = document.createElement('div');
//             test_function.setAttribute('id', 'testUnitFunction');
//             if (caseData.test_function) {
//                 test_function.innerText = caseData.test_function;
//             } else if (testButtonDataset.test_function) {
//                 test_function.innerText = caseData.test_function;
//             }
//             toastBase.childNodes[3].appendChild(test_function);
//         }
//
//     } else if (testButtonDataset.test_mode === 'test_by_change') {
//         testDetails.innerText = 'Will run all tests by cases change';
//         let testMetadataAttrs = document.createElement('div');
//         testMetadataAttrs.setAttribute('id', caseData.change);
//
//     } else if (testButtonDataset.test_mode === 'test_by_user') {
//         testDetails.innerText = 'Will run all test by cases user';
//         let testMetadataAttrs = document.createElement('div');
//         testMetadataAttrs.setAttribute('id', caseData.change_user);
//
//     } else if (testButtonDataset.test_mode === 'test_by_change_ticket') {
//         testDetails.innerText = 'Will run all tests by cases ticket';
//         let testMetadataAttrs = document.createElement('div');
//         testMetadataAttrs.setAttribute('id', caseData.change_ticket);
//
//     } else if (testButtonDataset.test_mode === 'test_by_change_review') {
//         testDetails.innerText = 'Will run all tests test by cases review';
//         let testMetadataAttrs = document.createElement('div');
//         testMetadataAttrs.setAttribute('id', caseData.change_review);
//
//     } else if (testButtonDataset.test_mode === 'test_by_multiple_ids') {
//         testDetails.innerText = 'Will run multiple cases by selected ids';
//         let testMetadataAttrs = document.createElement('div');
//         testMetadataAttrs.setAttribute('id', caseData.case_id);
//
//     } else {
//         testDetails.innerText = 'Will run test in other mode. Not yet implemented?'
//     }
//     // Add case and test details to toast body:
//     toastBody.append(testDetails);
//
//     if (testButtonDataset.wipe) {
//         testMode.innerText = `Wipe latest logs`;
//         toastBase.childNodes[3].appendChild(testMode);
//     } else if (testButtonDataset.refresh) {
//         testMode.innerText = `Run p4 sync, wipe latest logs`;
//         toastBase.childNodes[3].appendChild(testMode);
//     } else {
//         testMode.innerText = `Instant run, keep logs, no p4 sync`;
//         toastBase.childNodes[3].appendChild(testMode);
//     }
//
//     return toastBase
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal, testToast
//  * Already published toast now modifying with task id from POST request
//  * @param taskId
//  * @param toastId
//  */
// function toastModifyCaseDataPre(taskId, toastId) {
//     let toastPublished = document.getElementById(toastId);
//     let toastBody = toastPublished.childNodes[3];  // Path to toast body.
//     let taskIdDiv = document.createElement('div');  // toast-body
//     taskIdDiv.setAttribute('id', 'task_id');
//     taskIdDiv.innerText = `task: ${taskId}`;
//     toastBody.appendChild(taskIdDiv);
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal, testToast
//  * Get published toast by it's ID. We're assigning id by case_id, so it should be same.
//  * @param toastReady
//  */
// function appendToastToStack(toastReady) {
//     // Append new toast to toast stack container:
//     document.getElementById('toastStack').appendChild(toastReady);
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal, testToast
//  * Depends on data attributes from button make new dataset only with required attributes to run test task with POST
//  * @param caseData
//  * @param testButtonDataset
//  */
// function composeTestDataSet(caseData, testButtonDataset) {
//     if (testButtonDataset.test_mode === 'test_by_id') {
//         // Request selector use cases_ids for single and multiple cases anyway:
//         testButtonDataset.cases_ids = caseData.case_id;
//     } else if (testButtonDataset.test_mode === 'test_by_change') {
//         testButtonDataset.change = caseData.change;
//     } else if (testButtonDataset.test_mode === 'test_by_user') {
//         testButtonDataset.change_user = caseData.change_user;
//     } else if (testButtonDataset.test_mode === 'test_by_change_ticket') {
//         testButtonDataset.change_ticket = caseData.change_ticket;
//     } else if (testButtonDataset.test_mode === 'test_by_change_review') {
//         testButtonDataset.change_review = caseData.change_review;
//     } else if (testButtonDataset.test_mode === 'test_by_multiple_ids') {
//         testButtonDataset.cases_ids = caseData.cases_ids;
//     } else {
//     }
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal, testToast
//  * Time wait, before trying to get task data(status) by it's ID
//  * @param taskID
//  * @param toastId
//  */
// function waitResult(taskID, toastId) {
//     setTimeout(function () {
//         new RESTGetTask(taskID, toastId);
//     }, 5000);
// }
//
// /**
//  * For USER_TEST_RUN_FROM_TEST_CASE_TABLES, #actionsModal, testToast
//  * REST call to run user test task. Return task_id by default, if added.
//  * @param caseFullData - all attributes from test table row
//  * @param testButtonDataset - all attributes after cleaning for test run
//  * @param toastBase - toast base with id, to append task when added and after 15 sec wait
//  * @constructor
//  */
// function RESTPostTask(caseFullData, testButtonDataset, toastBase) {
//     console.log(`POST user test: `);
//     console.log(testButtonDataset);
//     $.ajax({
//         type: "POST",
//         dataType: "json",
//         contentType: "application/x-www-form-urlencoded",
//         url: "/octo_tku_patterns/user_test_add/",
//         data: testButtonDataset,
//         "beforeSend": function (xhr, settings) {
//             $.ajaxSettings.beforeSend(xhr, settings)
//         },
//         "success": function (result) {
//             // console.log(`POST result: ${result}`);
//             if (result.task_id) {
//                 // console.log("testButtonDataset after POST: ");
//                 // console.table(testButtonDataset);
//                 // On success - run get task status:
//                 toastModifyCaseDataPre(result.task_id, toastBase.id);
//                 waitResult(result.task_id, toastBase.id);
//             } else {
//                 console.log("Task POST send, but haven't been added. No task_id in result!")
//             }
//         },
//         "error": function () {
//             console.log("POST TASK ERROR, something goes wrong...")
//         },
//     });
// }
//
// /**
//  * REST GET request to obtain task status and data by task_id.
//  * If request is 'success' - try to modify published toast with same ID as case(or test) to show current task status
//  * @param taskID
//  * @param toastId
//  * @constructor
//  */
// function RESTGetTask(taskID, toastId) {
//     // console.log(`GET user test task by id: ${testButtonDataset.task_id}`);
//     $.ajax({
//         "type": "GET",
//         "dataType": "json",
//         contentType: "application/json; charset=utf-8",
//         "url": "/octo_tku_patterns/user_test_add/",
//         data: {task_id: taskID},
//         "beforeSend": function (xhr, settings) {
//             $.ajaxSettings.beforeSend(xhr, settings)
//         },
//         "success": function (result) {
//             // console.log(`GET result: ${result}`);
//             // console.table(result[0]);
//             let task = result[0];
//             if (task && task.status) {
//                 // console.log("caseFullData right after GET");
//                 // console.table(caseFullData);
//                 // On success - run toast modify:
//                 toastModifySuccess(task, toastId);
//             } else {
//                 console.log("Task GET failed, no task found or no status");
//             }
//         },
//         "error": function () {
//             console.log("GET TASK ERROR, something goes wrong...");
//         },
//     });
// }
//
// /**
//  * Already published toast now modifying with new data: when task has been added and GET request return it's data
//  * NOTE: It does not work while task is processing. Only when finished and saved to DB
//  * @param toastId
//  * @param taskObj
//  */
// function toastModifySuccess(taskObj, toastId) {
//     let toastPublished = document.getElementById(toastId);
//     let task_status = document.createElement('div');  // toast-body
//     task_status.setAttribute('id', 'task_status');
//     // console.log("Modifying toast with task:");
//     // console.table(caseFullData);
//     if (taskObj.state) {
//         task_status.innerText = `task: ${taskObj.status} - ${taskObj.state}`;
//     } else {
//         if (taskObj.status === 'FAILURE') {
//             task_status.innerText = `task: ${taskObj.status} - please check!`;
//         } else {
//             task_status.innerText = `task: ${taskObj.status} - wait in queue...`;
//         }
//     }
//     toastPublished.childNodes[3].appendChild(task_status);
// }
//
// function makeCaseTestDataSet(dataJSON, case_id) {
//     let caseTestDataset = [];
//         for (let testItem of dataJSON) {
//             if (parseInt(testItem['case_id']) === parseInt(case_id)) {
//                 // console.log(testItem);
//                 caseTestDataset.push(testItem);
//             }
//         }
//     return caseTestDataset
// }