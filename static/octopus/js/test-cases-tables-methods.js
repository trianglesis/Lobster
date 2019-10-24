/**
 * Methods
 */

/**
 * Returns table row dependent from this row's pushed button of modal or so.
 * Works for tables in test digests, ...
 * @param event
 * @returns {Node & ParentNode}
 */
function getTableRowFromEvent(event) {
    return event.relatedTarget.parentNode.parentNode;
}

/**
 * Return actual button which cause an event.
 * @param event
 * @returns {jQuery.fn.init|jQuery|HTMLElement}
 */
function getButtonFromEvent(event) {
    return $(event.relatedTarget); // Button that triggered the modal
}

/**
 *
 * @param tableRow
 * @returns {Object}
 */
function parseTableRowForCaseData(tableRow) {

    let caseData = new Object({
        tkn_branch: '',
        addm_name: '',
        pattern_library: '',
        pattern_folder_name: '',
        case_id: '',  // Use as default id for toast when interactive run test.
        test_id: '',  // When no case_id available (like on history or unit test) use this instead of case_id
        tst_class: '',
        tst_name: '',
        cases_ids: '',
        change_ticket: '',
        change_review: '',
        change_user: '',
        change: '',
        test_py_path: '',  // Use this as last stand to run main tests from history or digest tables, when no case_id present.
        test_function: '',
        wipe: '',
        refresh: '',
    });
    // Set tkn_branch if any:
    if (tableRow.cells['tkn_branch'].textContent) {
        caseData.tkn_branch = tableRow.cells['tkn_branch'].textContent;
        caseData.test_py_path = tableRow.cells['test_py_path'].textContent;
    } else {
        caseData.test_py_path = tableRow.cells['test_py_path'].textContent;
        console.log("There is no tkn_branch for this case, it's probably main test")
    }

    if (tableRow.cells['change_ticket'] && tableRow.cells['change_ticket'].textContent) {
        caseData.change_ticket = tableRow.cells['change_ticket'].textContent
    }
    if (tableRow.cells['change_review'] && tableRow.cells['change_review'].textContent) {
        caseData.change_review = tableRow.cells['change_review'].textContent
    }
    if (tableRow.cells['change_user'] && tableRow.cells['change_user'].textContent) {
        caseData.change_user = tableRow.cells['change_user'].textContent
    }
    if (tableRow.cells['change'] && tableRow.cells['change'].textContent) {
        caseData.change = tableRow.cells['change'].textContent
    }

    // On test case table (groups) we have no ADDM value
    if (tableRow.cells['addm_name'] && tableRow.cells['addm_name'].textContent) {
        caseData.addm_name = tableRow.cells['addm_name'].textContent;      // Get addm_name from tr, later use to compose link to see logs for that:
    } else {
        console.log("There is no addm_name column, it's probably a test case table.")
    }

    // On history logs we couldn't have a case_id for now.
    if (tableRow.cells['case_id'] && tableRow.cells['case_id'].textContent) {
        caseData.case_id = tableRow.cells['case_id'].textContent;
        caseData.cases_ids = tableRow.cells['case_id'].textContent;
    } else {
        // We use test_id as id for drawing toasts and so on.
        caseData.test_id = tableRow.cells['test_id'].textContent;
    }

    // Also on history table we have another nodes for case_unit tr > td > li
    if (tableRow.cells['pattern_library'] && tableRow.cells['pattern_folder_name'].textContent) {
        caseData.pattern_folder_name = tableRow.cells['pattern_folder_name'].textContent;
        caseData.pattern_library = tableRow.cells['pattern_library'].textContent;
        console.log(`This is pattern related case: ${caseData.pattern_folder_name} ${caseData.pattern_library}`);
    } else if (tableRow.cells['case_unit']) {
        // Try to find in li
        let case_unit = tableRow.cells['case_unit'];
        caseData.pattern_folder_name = case_unit.childNodes[0].textContent;  // document.querySelector("#case_unit > li.pattern_library")
        caseData.pattern_library = case_unit.childNodes[1].textContent;  // document.querySelector("#case_unit > li.pattern_folder_name")
        console.log(`This is pattern related case: ${caseData.pattern_folder_name} ${caseData.pattern_library}`);
    } else {
        console.log("Table cells cannot be found: 'pattern_library', 'pattern_folder_name', 'case_unit'");
        console.log(`This is test main related case: `);
    }

    // Unit test class and name is located on single cell with li tags:
    if (tableRow.cells['test_unit']) {
        let test_unit = tableRow.cells['test_unit'];
        caseData.tst_class = test_unit.childNodes[0].textContent;  // document.querySelector("#test_unit > li.tst_class")
        caseData.tst_name = test_unit.childNodes[1].textContent;  // document.querySelector("#test_unit > li.tst_name")
    } else {
        // If not found test unit:
        console.log("Table cell 'test_unit' not found, probably there is no test unit, but test.py")
    }

    // Check if we're on single test item and user wanted to run only one unit case
    let test_function;
    if (caseData.tst_class && caseData.tst_name) {
        caseData.test_function = `;test_function=${caseData.tst_class}+${caseData.tst_name}`;
    } else {
        // console.log("Current test run URL will execute test.py full");
    }
    // console.log("Parsed case data: ");
    // console.table(caseData);
    return caseData
}

/**
 * Try to get modal body with assigned test case attributes in it.
 * Attributes were added by: static/octopus/js/test-actions-modal.js
 * @param modalBody
 * @returns {Object}
 */
function parseModalBodyForCaseData(modalBody) {
    let modalBodyChildren = modalBody.childNodes[3].children;
    // console.table(modalBodyChildren);

    let caseData = new Object({
        tkn_branch: '',
        pattern_library: '',
        pattern_folder_name: '',
        case_id: modalBodyChildren['case_id'].textContent,
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

    if (modalBodyChildren['tkn_branch'].textContent && modalBodyChildren['pattern_library'].textContent) {
        caseData.tkn_branch = modalBodyChildren['tkn_branch'].textContent;
        caseData.pattern_library = modalBodyChildren['pattern_library'].textContent;
        caseData.pattern_folder_name = modalBodyChildren['pattern_folder_name'].textContent;
    }
    if (modalBodyChildren['case_id'].textContent) {
        console.log("This is not a pattern related case, use case ID to select and run test.");
        caseData.cases_ids = modalBodyChildren['case_id'].textContent;
    }
    if (modalBodyChildren['test_id'] && modalBodyChildren['test_id'].textContent) {
        caseData.test_id = modalBodyChildren['test_id'].textContent;
    } else {
        console.log("TODO: Assign other selectables by: change_ticket, change_review, change_user, change(p4) ");
    }

    return caseData
}

/**
 * Insert some parsed data of caseData in modal body
 * @param modal
 * @param caseData
 */
function fillModalBody(modal, caseData) {
    // Create in modal body:
    let modal_variables = modal.childNodes[1].childNodes[1].childNodes[3].childNodes[3];
    // Remove extra children if any found. Could be leftovers from previous modal draw!
    while (modal_variables.firstChild) {
        modal_variables.firstChild.remove();
    }
    // Fill modal body > modal variables with caseData attributes:
    for (const [key, value] of Object.entries(caseData)) {
        // console.log("Creating modal divs:" + key, value);
        if (value) {
            let div = document.createElement('div');
            div.setAttribute('id', key);
            // div.text(value);
            // div.innerText = `${key}: ${value}`;
            div.innerText = `${value}`;
            modal_variables.appendChild(div);
        }
    }
}

/**
 * Try to see if we have an addm_name in context, which could be passed here from button data.
 * This is required when user wants to sort out only addm related tests.
 * From test last table call modal with options:
 * data-target="#actionsModal" data-tst_status="{{ selector.tst_status }}" data-addm_name="{{ selector.addm_name }}"
 * then if true - we'll add this query to logs sort buttons. If not - just leave global query for all addm related logs.
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
        if (caseData.addm_name) {
            // Yes, there is no addm_name in context, but we activate JS-able tab in next page
            addm_name_url = `#${caseData.addm_name}`;
        }
    }
    return addm_name_url
}

/**
 * Same as for detectADDMSelectorFromContext, allow user to sort out only selected level of tests, when
 * user browse forward to see test_last -> test_test_details
 * @param button
 * @param caseData
 * @returns {string}
 */
function detectTestStatusSelectorFromContext(button, caseData) {
    let tst_status = button.data('tst_status');
    let tst_status_url = '';
    if (tst_status) {
        tst_status_url = `;tst_status=${tst_status}`;
    }
    caseData.tst_status = tst_status;
    return tst_status_url
}

/**
 * Make buttons for test run have required attributes to run test:
 * Single test.py modes: wipe-run, p4-run, instant-run
 * @param caseData
 */
function assignTestCaseTestButtons(caseData) {
    let test_wipe_run = document.getElementById("wipe-run");
    if (test_wipe_run) {
        test_wipe_run.setAttribute('data-cases_ids', caseData.cases_ids);
    }
    let test_p4_run = document.getElementById("p4-run");
    if (test_p4_run) {
        test_p4_run.setAttribute('data-cases_ids', caseData.cases_ids);
    }
    let test_instant_run = document.getElementById("instant-run");
    if (test_instant_run) {
        test_instant_run.setAttribute('data-cases_ids', caseData.cases_ids);
    }
}

/**
 * Make buttons for test run have required attributes to run test:
 * Single test.py modes: wipe-run, p4-run, instant-run
 * @param caseData
 */
function assignTestCaseUnitTestButtons(caseData) {
    // Test case Unit test run:
    let unit_wipe_run = document.getElementById("unit-wipe-run");
    if (unit_wipe_run) {
        unit_wipe_run.setAttribute('data-cases_ids', caseData.cases_ids);
        unit_wipe_run.setAttribute('data-test_functions', caseData.test_function);
    }
    let unit_p4_run = document.getElementById("unit-p4-run");
    if (unit_p4_run) {
        unit_p4_run.setAttribute('data-cases_ids', caseData.cases_ids);
        unit_p4_run.setAttribute('data-test_functions', caseData.test_function);
    }
    let unit_instant_run = document.getElementById("unit-instant-run");
    if (unit_instant_run) {
        unit_instant_run.setAttribute('data-cases_ids', caseData.cases_ids);
        unit_instant_run.setAttribute('data-test_functions', caseData.test_function);
    }
}

/**
 *
 * @param caseData
 * @param addm_name_url
 * @param tst_status_url
 */
function composeLogsHyperlinks(caseData, addm_name_url, tst_status_url) {
    let seeLogs = document.getElementById('see-logs');
    if (seeLogs) {
        if (caseData.tkn_branch) {
            // For when we have a usual pattern related case
            seeLogs.href = `/octo_tku_patterns/test_details/?tkn_branch=${caseData.tkn_branch};pattern_library=${caseData.pattern_library};pattern_folder_name=${caseData.pattern_folder_name}${tst_status_url}${addm_name_url}`;
        } else {
            // For when we have a main or octo test:
            seeLogs.href = `/octo_tku_patterns/test_details/?test_py_path=${caseData.test_py_path}${tst_status_url}${addm_name_url}`;
        }
    } else {
        // console.log("Cannot find element id for seeLogs " + seeLogs)
    }

    let seeLogsHist = document.getElementById('see-logs-history');
    if (seeLogsHist) {
        if (caseData.tkn_branch) {
            // For when we have a usual pattern related case
            if (caseData.tst_class && caseData.tst_name) {
                seeLogsHist.href = `/octo_tku_patterns/test_item_history/?tkn_branch=${caseData.tkn_branch};pattern_library=${caseData.pattern_library};pattern_folder_name=${caseData.pattern_folder_name};tst_class=${caseData.tst_class};tst_name=${caseData.tst_name}${tst_status_url}${addm_name_url}`;
            } else {
                seeLogsHist.href = `/octo_tku_patterns/test_item_history/?tkn_branch=${caseData.tkn_branch};pattern_library=${caseData.pattern_library};pattern_folder_name=${caseData.pattern_folder_name}${tst_status_url}${addm_name_url}`;
            }
        } else {
            // For when we have a main or octo test:
            if (caseData.tst_class && caseData.tst_name) {
                seeLogsHist.href = `/octo_tku_patterns/test_item_history/?test_py_path=${caseData.test_py_path};tst_class=${caseData.tst_class};tst_name=${caseData.tst_name}${tst_status_url}${addm_name_url}`;
            } else {
                seeLogsHist.href = `/octo_tku_patterns/test_item_history/?test_py_path=${caseData.test_py_path}${tst_status_url}${addm_name_url}`;
            }
        }
    } else {
        // console.log("Cannot find element id for seeLogsHist " + seeLogsHist)
    }
}

/**
 * Make links for case: edit, view, etc.
 * @param caseData
 */
function composeCaseHyperlinks(caseData) {
    let seeCaseInfo = document.getElementById('all-info');
    if (seeCaseInfo) {
        seeCaseInfo.href = `/octo_tku_patterns/test_case/${caseData.case_id}`;
    } else {
        // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
    }
    let editCase = document.getElementById('edit-case');
    if (editCase) {
        editCase.href = `/octo_tku_patterns/test_case/change/${caseData.case_id}`;
    } else {
        // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
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
    let modal_variables = modal.childNodes[1].childNodes[1].childNodes[3].childNodes[3];
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
 * Toast actions and methods.
 * Required when user push modal buttons. Each active (not browse) button have a data-attributes inserted:
 * Listen to action 'click' grab attributes from it and proceed toast generation.
 * Send POST with test task query and GET to check if task is actually added PENDING,STARTED ot FAILURE
 **/

/**
 *
 * @return dataset from button on event
 */
function eventListenerForCaseTestButtons(funcToRun) {
    // Test case testing
    let test_wipe_run = document.getElementById("wipe-run");
    let test_p4_run = document.getElementById("p4-run");
    let test_instant_run = document.getElementById("instant-run");

    if (test_wipe_run) {
        test_wipe_run.addEventListener("click", function () {
            console.log("test_wipe_run clisk");
            funcToRun(test_wipe_run.dataset);
        });
    }
    if (test_p4_run) {
        test_p4_run.addEventListener("click", function () {
            console.log("test_p4_run clisk");
            funcToRun(test_p4_run.dataset);
        });
    }
    if (test_instant_run) {
        test_instant_run.addEventListener("click", function () {
            console.log("test_instant_run clisk");
            funcToRun(test_instant_run.dataset);
        });
    }
}

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
 * Making a copy of toast draft HTML and assign new copy with unique case ID
 * TODO: If no case_id found - use unique case values set. (tkn_branch, library, patt_folder etc) or use test ID?
 * @param caseData
 * @returns {Node}
 */
function getToastDraftWithId(caseData) {
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
 * @param caseFullData
 * @returns {*}
 */
function fillToastBodyWithTestAttributes(toastBase, caseFullData) {
    let metaData = ['change_ticket', 'change_review', 'change_user', 'change'];
    let showPattern = true;

    for (const [key, value] of Object.entries(caseFullData)) {
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
        // When no metadata key,values found, just keep caseFullData with current keys.
        // They're usually patterns attributes or cases_ids.
        let tknBranchPattLib = document.createElement('div');  // toast-body
        let patternDirectory = document.createElement('div');  // toast-body

        tknBranchPattLib.setAttribute('id', 'tknBranchPattLib');
        patternDirectory.setAttribute('id', 'patternDirectory');

        tknBranchPattLib.innerText = `${caseFullData.tkn_branch} / ${caseFullData.pattern_library}`;
        patternDirectory.innerText = caseFullData.pattern_folder_name;

        toastBase.childNodes[3].appendChild(tknBranchPattLib);
        toastBase.childNodes[3].appendChild(patternDirectory);
    }

    let test_mode = document.createElement('div');  // toast-body
    test_mode.setAttribute('id', 'test_mode');
    if (caseFullData.wipe) {
        test_mode.innerText = `Wipe latest logs`;
        toastBase.childNodes[3].appendChild(test_mode);
    } else if (caseFullData.refresh) {
        test_mode.innerText = `Run p4 sync, wipe latest logs`;
        toastBase.childNodes[3].appendChild(test_mode);
    } else {
        test_mode.innerText = `Instant run, keep logs, no p4 sync`;
        toastBase.childNodes[3].appendChild(test_mode);
    }

    return toastBase
}

/**
 * Already published toast now modifying with task id from POST request
 * @param caseFullData
 */
function toastModifyPre(caseFullData) {
    console.log("toastModifyPre: caseFullData");
    console.table(caseFullData);
    let toastPublished = document.getElementById(caseFullData.toastId);
    let task_id = document.createElement('div');  // toast-body
    task_id.setAttribute('id', 'task_id');
    task_id.innerText = `task: ${caseFullData.task_id}`;
    toastPublished.childNodes[3].appendChild(task_id);
}

/**
 * Already published toast now modifying with new data: when task has been added and GET request return it's data
 * NOTE: It does not work while task is processing. Only when finished and saved to DB
 * @param caseFullData
 */
function toastModifySuccess(caseFullData) {
    let toastPublished = document.getElementById(caseFullData.toastId);
    let task_status = document.createElement('div');  // toast-body
    task_status.setAttribute('id', 'task_status');
    // console.log("Modifying toast with task:");
    // console.table(caseFullData);
    let task = caseFullData.task_obj;
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
 * REST
 **/

/**
 * Time wait, before trying to get task data(status) by it's ID
 * @param caseFullData
 * @param testButtonDataset
 */
function waitResult(caseFullData, testButtonDataset) {
    setTimeout(function () {
        new RESTGetTask(caseFullData, testButtonDataset);
    }, 5000);
}

/**
 * REST call to run user test task. Return task_id by default, if added.
 * @param caseFullData
 * @param testButtonDataset
 * @returns {*}
 * @constructor
 */
function RESTPostTask(caseFullData, testButtonDataset) {
    console.log(`POST user test: `);
    console.table(testButtonDataset);
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/x-www-form-urlencoded",
        url: "/octo_tku_patterns/user_test_add/",
        data: testButtonDataset,
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            // console.log(`POST result: ${result}`);
            if (result.task_id) {
                caseFullData.task_id = result.task_id;
                // console.log("testButtonDataset after POST: ");
                // console.table(testButtonDataset);
                // On success - run get task status:
                toastModifyPre(caseFullData, testButtonDataset);
                waitResult(caseFullData, testButtonDataset);
            } else {
                console.log("Task POST send, but haven't been added. No task_id in result!")
            }
        },
        "error": function () {
            console.log("POST TASK ERROR, something goes wrong...")
        },
    });
    return testButtonDataset;
}

/**
 * REST GET request to obtain task status and data by task_id.
 * If request is 'success' - try to modify published toast with same ID as case(or test) to show current task status
 * @param caseFullData
 * @param testButtonDataset
 * @returns {*}
 * @constructor
 */
function RESTGetTask(caseFullData, testButtonDataset) {
    // console.log(`GET user test task by id: ${testButtonDataset.task_id}`);
    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/octo_tku_patterns/user_test_add/",
        data: {task_id: caseFullData.task_id},
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            // console.log(`GET result: ${result}`);
            // console.table(result[0]);
            let task = result[0];
            if (task && task.status) {
                caseFullData.task_obj = task;
                // console.log("caseFullData right after GET");
                // console.table(caseFullData);
                // On success - run toast modify:
                toastModifySuccess(caseFullData);
            } else {
                console.log("Task GET failed, no task found or no status");
            }
        },
        "error": function () {
            console.log("GET TASK ERROR, something goes wrong...");
        },
    });
    return testButtonDataset;
}


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

