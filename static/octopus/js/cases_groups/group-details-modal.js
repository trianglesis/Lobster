/**
 *
 * Group of test cases modal
 *
 * This is a launcher of modal for pattern test case on page /octo_tku_patterns/test_cases_group/1/
 * Here all data for case if present, like ID, Pattern folder change, tickets and metadata from p4.
 * Parse data from table row where modal button was pressed,
 *  - compose hyperlinks to browse case, and detailed logs
 *  Later: assign event listeners to test run buttons.
 */

$(document).ready(function () {
    $('#actionsModal').on('hidden.bs.modal', function (event) {
        $('#actionsModal').modal('hide');
    });
});

$(document).ready(function () {
    $('#mulCasesModal').on('hidden.bs.modal', function (event) {
        $('#mulCasesModal').modal('hide');
    });
});

/**
 * This modal activates on single case row, on button Actions
 */
$(document).ready(function () {
    //Opening of modal action
    $('#actionsModal').on('show.bs.modal', function (event) {
        // let modal_ = $(this);
        let modal = document.getElementById("actionsModal");
        let tableRow = getTableRowFromEvent(event);
        let caseData = parseTableRowForCaseData(tableRow);
        // console.table(caseData);

        // Fill modal body with divs:
        // Arr of ids will be not be shown to user as visible in modal-variables
        let excludeIds = ['case_depot_path', 'test_time_weight', 'test_cases_group', 'change_time'];
        fillModalBody(modal, caseData, excludeIds);

        // No need to get addm or test status on group page;
        composeLogsHyperlinks(caseData, '', '');
        assignTestCaseTestButtons(caseData);
        composeCaseHyperlinks(caseData);
    });
});

/**
 * This modal activates on group container, on the button 'Run All'
 */
$(document).ready(function () {
    //Opening of modal action
    $('#mulCasesModal').on('show.bs.modal', function (event) {
        let modal = document.getElementById("mulCasesModal");
        let tableOfCasesRows = tableCases(event);
        let casesData = collectCasesFromRows(tableOfCasesRows);

        // console.log("mulCasesModal casesData:");
        // console.table(casesData);

        fillModalBodyWithMultipleCases(modal, casesData);
        // Draw a button for test run:
        fillButtonTestRun(modal, casesData);
        // console.table(casesData);
        // When buttons are ready - lets wait for actions on them:
    });
});