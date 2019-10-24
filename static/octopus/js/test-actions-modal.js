$(document).ready(function () {
    $('#actionsModal').on('hidden.bs.modal', function (event) {
        $('#actionsModal').modal('hide');
    });
});

$(document).ready(function () {
    //Opening of modal action
    $('#actionsModal').on('show.bs.modal', function (event) {
        // let modal_ = $(this);
        let modal = document.getElementById("actionsModal");
        let tableRow = getTableRow(event);
        let button = getButton(event);
        let caseData = parseTableRow(tableRow);
        // console.table(caseData);

        // Fill modal body with divs:
        fillModalBody(modal, caseData);

        // Paste hypelinks on buttons with log views:
        let addm_name_url = detectADDMSelector(button, caseData);
        let tst_status_url = detectTestStatusSelector(button, caseData);
        composeHyperlinks(caseData, addm_name_url, tst_status_url)
    });

});

function getTableRow(event) {
    return event.relatedTarget.parentNode.parentNode;
}

function getButton(event) {
    return $(event.relatedTarget); // Button that triggered the modal
}

function parseTableRow(tableRow) {

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
    });
    // Set tkn_branch if any:
    if (tableRow.cells['tkn_branch'].textContent) {
        caseData.tkn_branch = tableRow.cells['tkn_branch'].textContent;
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
    if (tableRow.cells['addm_name']  && tableRow.cells['addm_name'].textContent) {
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
        // console.log("Current test run URL will include 'test_function' attribute");
        test_function = `;test_function=${caseData.tst_class}+${caseData.tst_name}`;
    } else {
        // console.log("Current test run URL will execute test.py full");
    }
    // console.log("Parsed case data: ");
    // console.table(caseData);
    return caseData
}

function fillModalBody(modal, caseData) {
    // Create in modal body:
    let modal_variables = modal.childNodes[1].childNodes[1].childNodes[3].childNodes[3];
    // console.log('Modal modal-variables has children - remove them!');
    while (modal_variables.firstChild) {
        modal_variables.firstChild.remove();
    }
    for (const [key, value] of Object.entries(caseData)) {
        // console.log("Creating modal divs:" + key, value);
        let div = document.createElement('div');
        div.setAttribute('id', key);
        // div.text(value);
        div.innerText = `${value}`;
        modal_variables.appendChild(div);
    }
}

function detectADDMSelector(button, caseData) {
    let addm_name_url = '';
    // Add addm_name attribute for sort OR to activate tab
    if (button.data('addm_name') && button.data('addm_name') !== 'None') {
        addm_name_url = `;addm_name=${button.data('addm_name')}`;
    } else {
        if (caseData.addm_name) {
            addm_name_url = `#${caseData.addm_name}`;
        }
    }
    return addm_name_url
}

function detectTestStatusSelector(button, caseData) {
    let tst_status = button.data('tst_status');
    let tst_status_url = '';
    if (tst_status) {
        tst_status_url = `;tst_status=${tst_status}`;
    }
    caseData.tst_status = tst_status;
    return tst_status_url
}

function composeHyperlinks(caseData, addm_name_url, tst_status_url) {
    // Insert data into buttons:
    // General test run:
    console.table(caseData);
    let test_wipe_run = document.getElementById("wipe-run");
    let test_p4_run = document.getElementById("p4-run");
    let test_instant_run = document.getElementById("instant-run");

    if (test_wipe_run) {
        test_wipe_run.setAttribute('data-cases_ids', caseData.cases_ids);
    }
    if (test_p4_run) {
        test_p4_run.setAttribute('data-cases_ids', caseData.cases_ids);
    }
    if (test_instant_run) {
        test_instant_run.setAttribute('data-cases_ids', caseData.cases_ids);
    }

    // Test case Unit test run:
    let unit_wipe_run  = document.getElementById("unit-wipe-run");
    if (unit_wipe_run) {
        unit_wipe_run.setAttribute('data-cases_ids', caseData.cases_ids);
    }
    let unit_p4_run  = document.getElementById("unit-p4-run");
    if (unit_p4_run) {
        unit_p4_run.setAttribute('data-cases_ids', caseData.cases_ids);
    }
    let unit_instant_run  = document.getElementById("unit-instant-run");
    if (unit_instant_run) {
        unit_instant_run.setAttribute('data-cases_ids', caseData.cases_ids);
    }

    let seeLogs = document.getElementById('see-logs');
    let seeLogsHist = document.getElementById('see-logs-history');
    let seeCaseInfo = document.getElementById('all-info');
    let editCase = document.getElementById('edit-case');

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
    if (seeCaseInfo) {
        seeCaseInfo.href = `/octo_tku_patterns/test_case/${caseData.case_id}`;
    } else {
        // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
    }
    if (editCase) {
        editCase.href = `/octo_tku_patterns/test_case/change/${caseData.case_id}`;
    } else {
        // console.log("Cannot find element id for seeCaseInfo " + seeCaseInfo)
    }
}