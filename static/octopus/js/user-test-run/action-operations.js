/**
 * MODAL OPERATIONS:
 */

function getButtonFromEvent(event) {
    return $(event.relatedTarget); // Button that triggered the modal
}

function secondsToTime(secNum) {
    let hours = Math.floor(secNum / 3600);
    let minutes = Math.floor((secNum - (hours * 3600)) / 60);
    let seconds = secNum - (hours * 3600) - (minutes * 60);
    return hours + ':' + minutes + ':' + seconds;

}

/**
 *
 * @param {Array} dataJSON
 * @param {string} case_id
 * @param testPyPath
 * @param casesIds
 * @returns {[]}
 */
function makeCaseTestDataSet(dataJSON,
                             case_id = undefined,
                             testPyPath = undefined,
                             casesIds = []) {
    let temp = [];
    let caseTestDataArr = [];
    for (let testItem of dataJSON) {
        //For case on last test
        if (case_id && (parseInt(testItem['case_id']) === parseInt(case_id))) {
            // console.log(testItem);
            caseTestDataArr.push(testItem);
            // For test on test details tables
        } else if (case_id && (parseInt(testItem['id']) === parseInt(case_id))) {
            caseTestDataArr.push(testItem);
            // For test in found or when need to sort out related items from JSON by test_py_path
        } else if (testPyPath && (testItem['test_py_path'] === testPyPath)) {
            caseTestDataArr.push(testItem);
            // For multiple selection via checkboxes. Compare page QS JSON with array of casesIds (from checkboxes)
        } else if (casesIds && casesIds[0]) {
            if (casesIds.includes(testItem['id']) || casesIds.includes(testItem['case_id'])) {

                // For test last digest where case is presented by "case_id"
                if (testItem['case_id']) {
                    if (temp.includes(testItem['case_id'])) {
                    } else {
                        temp.push(testItem['case_id']);
                        caseTestDataArr.push(testItem);
                    }
                }
                // For cases id in test cases table (not tests)
                if (testItem['id']) {
                    if (temp.includes(testItem['id'])) {
                    } else {
                        temp.push(testItem['id']);
                        caseTestDataArr.push(testItem);
                    }
                }
            }
        }
    }
    return caseTestDataArr
}

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

/**
 *
 * @param {HTMLElement} modal
 * @param testItemsJSON
 * @param {Array} caseAttrs
 */
function fillModalBodyNew(modal, testItemsJSON, caseAttrs) {
    let firstItem = '';
    // Create in modal body:
    let modal_variables = document.getElementById('modal-variables');
    // Remove extra children if any found. Could be leftovers from previous modal draw!
    while (modal_variables.firstChild) {
        modal_variables.firstChild.remove();
    }

    // Check if array with multiple cases\tests or single JSON item from REST or whatever:
    if (testItemsJSON && testItemsJSON[0]) {
        // When test items came from page view via django template tag: QS to JSON (serializer)
        firstItem = testItemsJSON[0];
    } else {
        // When test items came from REST request - this is single case DataSet
        firstItem = testItemsJSON;
    }

    // Make modal body block with case details from arr below:
    for (let attrK of caseAttrs) {
        let div = document.createElement('div');
        div.setAttribute('id', attrK);
        div.innerText = firstItem[attrK];
        modal_variables.appendChild(div);
    }

}

function fillModalBodyWithMultipleCases(modal, relCases) {
    // Create in modal body:
    let modal_variables = document.getElementById('modal-variables');
    // Remove extra children if any found. Could be leftovers from previous modal draw!
    while (modal_variables.firstChild) {
        modal_variables.firstChild.remove();
    }

    // Make count of all selected cases:
    let all_cases_count = document.createElement('div');
    all_cases_count.innerText = `All cases selected to run: ${relCases.length}`;
    // Make ETA sum of all test weight indexes
    let all_cases_sum_t_weight = document.createElement('div');
    let testsETA = 0;
    for (let caseItem of relCases) {
        if (caseItem['test_time_weight']) {
            testsETA = testsETA + parseInt(caseItem['test_time_weight']);
        } else {
            testsETA = testsETA + 300;
        }
    }
    all_cases_sum_t_weight.innerText = `All test time ETA hrs: ${secondsToTime(testsETA)}`;
    // Etc

    modal_variables.appendChild(all_cases_count);
    modal_variables.appendChild(all_cases_sum_t_weight);

}

/**
 *
 * @param testItemsJSON
 */
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

/**
 *
 * @param button
 * @param caseData
 * @returns {string}
 */
function detectADDMSelectorFromContext(button, caseData) {
    let addm_name_url = '';
    // Add addm_name attribute for sort OR to activate tab
    if (button.data('addm_name') && button.data('addm_name') !== 'None') {
        addm_name_url = `;addm_name=${button.data('addm_name')}`;
    } else {
        //TODO: Check if this is an Array of related cases, if so - use addm_name from else
        if (caseData && caseData.addm_name) {
            // Yes, there is no addm_name in context, but we activate JS-able tab in next page
            console.log(`Yes, there is no addm_name in context, but we activate JS-able tab in next page: ${caseData}`);
            addm_name_url = `#${caseData.addm_name}`;
        } else {
            console.log(`Case data has no addm_name in it, try something else: ${caseData}`);
            // Do not try to get addm_name when we are not in any test results page:
            let btn_to_cells =  button[0].parentNode.parentNode.cells;
            if (btn_to_cells && btn_to_cells['addm_name']) {
                let addm_name_cell =  btn_to_cells['addm_name'].textContent;
                console.log(`Addm name from cell where button was pushed: ${addm_name_cell}`);
                addm_name_url = `#${addm_name_cell}`;
            }
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

/**
 *
 * @param caseDataJSON
 * @param {string} addm_name_url
 * @param {string} tst_status_url
 */
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
        if (seeLogs.style && seeLogs.style.display === 'none') {
            seeLogs.style.display = 'inline-block'
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
        if (seeLogsHist.style && seeLogsHist.style.display === 'none') {
            seeLogsHist.style.display = 'inline-block'
        }
    } else {
        // console.log("Cannot find element id for seeLogsHist " + seeLogsHist)
    }
}

/**
 *
 * @param {string} caseId usually an array of case/tests data in json format. Pass array with single item
 * for cases gained from REST request or single selection.
 */
function composeCaseHyperlinksNew(caseId) {
    let seeCaseInfo = document.getElementById('all-info');
    if (seeCaseInfo) {
        seeCaseInfo.href = `/octo_tku_patterns/test_case/${caseId}`;
        if (seeCaseInfo.style && seeCaseInfo.style.display === 'none') {
            seeCaseInfo.style.display = 'inline-block'
        }
    } else {
        // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
    }
    let editCase = document.getElementById('edit-case');
    if (editCase) {
        editCase.href = `/octo_tku_patterns/test_case/change/${caseId}`;
        if (editCase.style && editCase.style.display === 'none') {
            editCase.style.display = 'inline-block'
        }
    } else {
        // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
    }
}

/**
 * In some cases we don't want to show links to logs, for example:
 * - when /test_cases_group/ select Run all
 * - any other place where cases/tests selected multiple.
 */
function hideHyperlinks() {
    let seeLogs = document.getElementById('see-logs');
    let seeLogsHist = document.getElementById('see-logs-history');
    let seeCaseInfo = document.getElementById('all-info');
    let editCase = document.getElementById('edit-case');

    if (seeLogs && seeLogs.style) {
        seeLogs.style.display = 'none';
    }
    if (seeLogsHist && seeLogsHist.style) {
        seeLogsHist.style.display = 'none';
    }
    if (seeCaseInfo && seeCaseInfo.style) {
        seeCaseInfo.style.display = 'none';
    }
    if (editCase && editCase.style) {
        editCase.style.display = 'none';
    }

}

function makeMultipleCasesIdsStr(relCases) {
    let multipleCases = [];
    if (relCases && relCases[0]) {
        for (let testCase of relCases) {
            multipleCases.push(testCase['id']);
        }
    } else {
        console.log('relCases array is empty! ' + relCases)
    }
    return multipleCases.join(',');
}

/**
 *
 * @param {string} caseId caseDataJSON usually an array of case/tests data in json format. Pass array with single item
 * for cases gained from REST request or single selection.
 * @param multipleCases
 */
function assignTestCaseTestButtonsNew(caseId, multipleCases = false) {
    let test_wipe_run = document.getElementById(
        "wipe-run");
    if (test_wipe_run) {
        test_wipe_run.setAttribute('data-case_id', caseId);
        if (multipleCases) {
            test_wipe_run.setAttribute('data-multiple_cases', 'true');
        } else {
            test_wipe_run.removeAttribute('data-multiple_cases')
        }
    }
    let test_p4_run = document.getElementById(
        "p4-run");
    if (test_p4_run) {
        test_p4_run.setAttribute('data-case_id', caseId);
        if (multipleCases) {
            test_p4_run.setAttribute('data-multiple_cases', 'true');
        } else {
            test_p4_run.removeAttribute('data-multiple_cases')
        }
    }
    let test_instant_run = document.getElementById(
        "instant-run");
    if (test_instant_run) {
        test_instant_run.setAttribute('data-case_id', caseId);
        if (multipleCases) {
            test_instant_run.setAttribute('data-multiple_cases', 'true');
        } else {
            test_instant_run.removeAttribute('data-multiple_cases')
        }
    }
}

/**
 * Make buttons for test run have required attributes to run test:
 * Single test.py modes: wipe-run, p4-run, instant-run
 * @param {Array} caseDataJSON caseDataJSON usually an array of case/tests data in json format. Pass array with single item
 * for cases gained from REST request or single selection.
 */
function assignTestCaseUnitTestButtons(caseDataJSON) {
    let caseData = caseDataJSON;
    // Test case Unit test run:
    let unit_wipe_run = document.getElementById("unit-wipe-run");
    let unit_p4_run = document.getElementById("unit-p4-run");
    let unit_instant_run = document.getElementById("unit-instant-run");

    // Switching visibility of some blocks and block names, when they do not needed:
    let CaseUnitModalButtons = document.getElementsByClassName("case-unit-modal-buttons");
    let TestActionsModalName = document.getElementsByClassName("test-actions-modal-name");
    let SeeLogsHistory = document.getElementById("see-logs-history");

    if (caseData['tst_class'] && caseData['tst_name']) {
        if (CaseUnitModalButtons[0]) {
            CaseUnitModalButtons[0].style.display = 'block';
        }
        if (TestActionsModalName[0]) {
            TestActionsModalName[0].style.display = 'block';
        }
        if (SeeLogsHistory) {
            SeeLogsHistory.style.display = 'block';
        }

        console.log(unit_wipe_run.dataset);
        let testMethodSpan = document.getElementById("test-method");
        // testMethodSpan.innerText = ''; // Clear previous?
        testMethodSpan.innerText = ` ${caseData['tst_class']}.${caseData['tst_name']}`;

        unit_wipe_run.style.display = 'block';
        unit_p4_run.style.display = 'block';
        unit_instant_run.style.display = 'block';

        if (unit_wipe_run) {
            unit_wipe_run.setAttribute(
                'data-case_id', caseData['case_id']);
            unit_wipe_run.setAttribute(
                'data-test_function',
                `${caseData['tst_class']}+${caseData['tst_name']}`);
        }
        if (unit_p4_run) {
            unit_p4_run.setAttribute(
                'data-case_id', caseData['case_id']);
            unit_p4_run.setAttribute(
                'data-test_function',
                `${caseData['tst_class']}+${caseData['tst_name']}`);
        }
        if (unit_instant_run) {
            unit_instant_run.setAttribute(
                'data-case_id', caseData['case_id']);
            unit_instant_run.setAttribute(
                'data-test_function',
                `${caseData['tst_class']}+${caseData['tst_name']}`);
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
 * TOAST OPERATIONS:
 */

/**
 *
 * @param {function} funcToRun
 */
function eventListenerForCaseTestButtons(funcToRun) {
    // Test case testing
    let test_wipe_run = document.getElementById("wipe-run");
    let test_p4_run = document.getElementById("p4-run");
    let test_instant_run = document.getElementById("instant-run");
    // Clear buttons dataset from any extra options:
    let testButtonUseKeys = ['wipe', 'refresh', 'test_mode', 'test_function', 'multiple_cases'];

    if (test_wipe_run) {
        test_wipe_run.addEventListener("click", function () {
            let testButtonDataset = new Object({'test_mode': '', 'multiple_cases': undefined});
            // console.log("test_wipe_run click");
            // console.log(test_wipe_run.dataset);
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
            let testButtonDataset = new Object({'test_mode': '', 'multiple_cases': undefined});
            // console.log("test_p4_run click");
            // console.log(test_p4_run.dataset);
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
            let testButtonDataset = new Object({'test_mode': '', 'multiple_cases': undefined});
            // console.log("test_instant_run click");
            // console.log(test_instant_run.dataset);
            for (let [key, value] of Object.entries(test_instant_run.dataset)) {
                if (testButtonUseKeys.includes(key)) {
                    testButtonDataset[key] = value;
                }
            }
            funcToRun(testButtonDataset);
        });
    }

    // Case Unit testing:
    let unit_wipe_run = document.getElementById("unit-wipe-run");
    let unit_p4_run = document.getElementById("unit-p4-run");
    let unit_instant_run = document.getElementById("unit-instant-run");


    if (unit_wipe_run) {
        unit_wipe_run.addEventListener("click", function () {
            let testButtonDataset = new Object({'test_mode': ''});
            // console.log("unit_wipe_run click");
            for (let [key, value] of Object.entries(unit_wipe_run.dataset)) {
                if (testButtonUseKeys.includes(key)) {
                    testButtonDataset[key] = value;
                }
            }
            funcToRun(testButtonDataset);
        });
    }
    if (unit_p4_run) {
        unit_p4_run.addEventListener("click", function () {
            let testButtonDataset = new Object({'test_mode': ''});
            // console.log("unit_p4_run click");
            for (let [key, value] of Object.entries(unit_p4_run.dataset)) {
                if (testButtonUseKeys.includes(key)) {
                    testButtonDataset[key] = value;
                }
            }
            funcToRun(testButtonDataset);
        });
    }
    if (unit_instant_run) {
        unit_instant_run.addEventListener("click", function () {
            let testButtonDataset = new Object({'test_mode': ''});
            // console.log("unit_instant_run click");
            for (let [key, value] of Object.entries(unit_instant_run.dataset)) {
                if (testButtonUseKeys.includes(key)) {
                    testButtonDataset[key] = value;
                }
            }
            funcToRun(testButtonDataset);
        });
    }

}

/**
 *
 * @param {Set} caseData
 * @param alterId
 */
function getToastDraftWithId(caseData, alterId = undefined) {
    let toastDraft = document.getElementById('toastDraft'); // Get draft toast from page foot
    let toastBase = toastDraft.children[0].cloneNode(true);  // Toast object

    // Set toast values:
    toastBase.setAttribute('data-delay', 30000); // 30 sec. Wait to task mod
    // Assign new toast copy a value ID based on item ID (case id or case unique attrs)
    if (caseData) {
        if (caseData['case_id']) {
            toastBase.id = caseData['case_id'];
        } else if (caseData['cases_ids']) {
            toastBase.id = caseData['cases_ids'];
        } else if (caseData['test_id']) {
            toastBase.id = caseData['test_id'];
        } else {
            toastBase.id = `${caseData['tkn_branch']}_${caseData['pattern_library']}_${caseData['pattern_folder_name']}`;
        }
    } else if (alterId) {
        toastBase.id = alterId;
    } else {
        toastBase.id = 'NoId-UseDefault';
        console.log('WARNING: There is no unique attributes to assign as toast ID, use default!')
    }

    // Toast elements:
    // toastBase.childNodes[1];  // toast-header
    // toastBase.childNodes[3];  // toast-body
    return toastBase
}

function getToastDraft(btnDataSet) {
    let toastDraft = document.getElementById('toastDraft'); // Get draft toast from page foot
    let toastBase = toastDraft.children[0].cloneNode(true);  // Toast object
    toastBase.setAttribute('data-delay', 30000); // 30 sec. Wait to task mod
    // Assign new toast copy a value ID based on item ID (case id or case unique attrs)
    console.log(btnDataSet);


    if (btnDataSet.operation_key && btnDataSet.command_key && btnDataSet.addm_group) {
        toastBase.id = `${btnDataSet.operation_key.replace(/\./g, '__dot__')}-${btnDataSet.command_key.replace(/\./g, '__dot__')}-${btnDataSet.addm_group}`;

    } else if (btnDataSet.addm_host && btnDataSet.command_key) {
        toastBase.id = `${btnDataSet.addm_host}-${btnDataSet.command_key.replace(/\./g, '__dot__')}`;

    } else if (btnDataSet.addm_host && btnDataSet.operation_key) {
        toastBase.id = `${btnDataSet.addm_host}-${btnDataSet.operation_key.replace(/\./g, '__dot__')}`;

    } else if (btnDataSet.addm_group && btnDataSet.command_key) {
        toastBase.id = `${btnDataSet.addm_group}-${btnDataSet.command_key.replace(/\./g, '__dot__')}`;

    } else {
        toastBase.id = `${btnDataSet.operation_key.replace(/\./g, '__dot__')}`;
    }
    return toastBase
}

/**
 *
 * @param {HTMLObjectElement} toastBase
 * @param {set} caseData
 * @param testButtonDataset
 * @returns {*}
 */
function fillToastBodyWithTestAttributes(toastBase, caseData, testButtonDataset) {
    let toastBody = toastBase.childNodes[3];  // Path to toast body.
    let testDetails = document.createElement('div');
    testDetails.setAttribute('id', testButtonDataset.test_mode);
    // Depend on data-test_mode="" attribute fill toast with caseData details:
    if (testButtonDataset.test_mode === 'test_by_id') {
        testDetails.innerText = 'Will run test by case id';
        if (testButtonDataset.multiple_cases && (testButtonDataset.multiple_cases = true)) {
            // Multiple cases run:
            console.log("fillToastBodyWithTestAttributes: Multiple cases run!");
            let casesIds = document.createElement('div');
            casesIds.setAttribute('id', 'multiple_cases');
            casesIds.innerText = `ids:${caseData}`;
            casesIds.style.wordWrap = 'break-word';
            toastBody.appendChild(casesIds);
        } else {
            // Single case run:
            // console.log("fillToastBodyWithTestAttributes: Single case run!");
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
    let testMode = document.createElement('div');
    testMode.setAttribute('id', 'test_mode');
    if (testButtonDataset.wipe) {
        testMode.innerText = `Wipe latest logs`;
    } else if (testButtonDataset.refresh) {
        testMode.innerText = `Run p4 sync, wipe latest logs`;
    } else {
        testMode.innerText = `Instant run, keep logs, no p4 sync`;
    }
    toastBody.append(testMode);

    return toastBase
}

/**
 *
 * @param {HTMLObjectElement} toastReady
 */
function appendToastToStack(toastReady) {
    // Append new toast to toast stack container:
    document.getElementById('toastStack').appendChild(toastReady);
}

/**
 *
 * @param caseData
 * @param testButtonDataset
 */
function composeTestDataSet(caseData, testButtonDataset) {
    if (testButtonDataset.test_mode === 'test_by_id') {
        // Request selector use cases_ids for single and multiple cases anyway:
        if (caseData['case_id']) {
            // For test_last digest where QS have attr case_id in it:
            testButtonDataset.cases_ids = caseData['case_id'];
        } else if (caseData['id']) {
            // For test details, history, search or other places, where case data gathered with REST request
            // using test attributes.
            testButtonDataset.cases_ids = caseData['id'];
        }
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

/**
 *
 * @param testButtonDataset
 * @param toastBase
 * @constructor
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
            if (result.task_id) {
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
 * @param {set} caseData - DataSet of test details log, usually. Or DataSet with 'test_py_path' attribute
 * @param {function} callThen
 * @constructor
 */
function RESTGetCaseByTestPyPath(caseData, callThen) {
    console.log(`RESTGetCaseByTestPyPath: ${caseData['test_py_path']}`);
    let caseItem = {};
    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/api/v1/cases/octo_test_cases/",
        data: {test_py_path: caseData['test_py_path']},
        "beforeSend": function (xhr, settings) {
            $.ajaxSettings.beforeSend(xhr, settings)
        },
        "success": function (result) {
            let caseItem = result.results[0];
            if (caseItem && caseItem.id) {
                console.log(`RESTGetCaseByTestPyPath result: ${caseItem.id} - ${caseItem.test_py_path}`);
                callThen(caseItem);
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

/**
 *
 * @param taskId
 * @param toastId
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

/**
 *
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

/**
 *
 * @param taskObj
 * @param toastId
 */
function toastModifySuccess(taskObj, toastId) {
    let toastPublished = document.getElementById(toastId);
    let task_status = document.createElement('div');  // toast-body
    task_status.setAttribute('id', 'task_status');
    // console.log("Modifying toast with task:");
    // console.table(caseFullData);
    if (taskObj.state) {
        task_status.innerText = `task: ${taskObj.status} - ${taskObj.state}`;
        task_status.setAttribute('class', 'task_status-state');
    } else {
        if (taskObj.status === 'FAILURE') {
            task_status.innerText = `task: ${taskObj.status} - please check!`;
            task_status.setAttribute('class', 'task_status-failed');
        } else {
            task_status.innerText = `task: ${taskObj.status} - wait in queue...`;
            task_status.setAttribute('class', 'task_status-queue');
        }
    }
    toastPublished.childNodes[3].appendChild(task_status);
}


/**
 * ADMIN OPTIONS:
 */
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
    $('#' + toastReady.id).toast('show');
    if (btn.modalId) {
        $('#' + btn.modalId).modal('hide');
    }
}

// Later make one:
function buttonActivationUpload(event) {
    let btn = event.currentTarget;
    let toastBase = getToastDraft(btn.dataset);
    let toastReady = fillToastBodyWithTaskDetails(btn.dataset, toastBase);
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    RESTUploadOperationsPOST(btn.dataset, toastReady);
    $('#' + toastReady.id).toast('show');
    if (btn.modalId) {
        $('#' + btn.modalId).modal('hide');
    }
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
 * REST ADMIN OPTIONS:
 */

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
        "beforeSend": function (xhr, settings) {
            $.ajaxSettings.beforeSend(xhr, settings)
        },
        "success": function (result) {
            console.log(result);
            let task = result.response;
            if (task && task.status) {
                toastModifyOtherTaskSuccess(toastReady, task);
            } else if (task) {
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
        "beforeSend": function (xhr, settings) {
            $.ajaxSettings.beforeSend(xhr, settings)
        },
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
        "beforeSend": function (xhr, settings) {
            $.ajaxSettings.beforeSend(xhr, settings)
        },
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