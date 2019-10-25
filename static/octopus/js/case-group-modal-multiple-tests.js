$(document).ready(function () {
    $('#mulCasesModal').on('hidden.bs.modal', function (event) {
        $('#mulCasesModal').modal('hide');
    });
});

$(document).ready(function () {
    //Opening of modal action
    $('#mulCasesModal').on('show.bs.modal', function (event) {
        // console.log("Modal cases Multiple show");
        // let modal_ = $(this);
        let modal = document.getElementById("mulCasesModal");
        // Get table rows
        let tableOfCasesRows = tableCases(event);
        // Parse cases table and create cases object
        let casesData = collectCasesFromRows(tableOfCasesRows);
        // Fill modal body with cases data to show user list of cases to be executed and calculated EST time
        fillModalBody(modal, casesData);
        // Draw a button for test run:
        fillButtonTestRun(modal, casesData);
        // console.table(casesData);
        // When buttons are ready - lets wait for actions on them:
    });

});

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
function fillModalBodyMultipleCases(modal, casesData) {
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