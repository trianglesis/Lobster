$(document).ready(function () {
    $('#addmUIButtonsModal').on('hidden.bs.modal', function (event) {
        $('#addmUIButtonsModal').modal('hide');
    });
});
$(document).ready(function () {
    $('#addmCleanupButtons').on('hidden.bs.modal', function (event) {
        $('#addmCleanupButtons').modal('hide');
    });
});
$(document).ready(function () {
    $('#addmCMDRun').on('hidden.bs.modal', function (event) {
        $('#addmCMDRun').modal('hide');
    });
});
$(document).ready(function () {
    $('#addmSYNCButtons').on('hidden.bs.modal', function (event) {
        $('#addmSYNCButtons').modal('hide');
    });
});
$(document).ready(function () {
    $('#addmServiceButtonsModal').on('hidden.bs.modal', function (event) {
        $('#addmServiceButtonsModal').modal('hide');
    });
});

/**
 * GENERAL FUNCTIONS:
 */

/**
 * Collect all selected commands from select multiple form by ID of this form
 * @param elementId
 * @returns {[]}
 */
function addmCMDkeysSelected(elementId) {
    let selectedCMDs = [];
    let selectBox = document.getElementById(elementId);
    let allOptions = selectBox.options;
    for (let selected of allOptions) {
        if (selected.selected) {
            if (selectedCMDs.includes(selected.value)) {
                console.log('Already selected')
            } else {
                selectedCMDs.push(selected.value);
            }
        }
    }
    console.log(selectedCMDs);
    return selectedCMDs;
}

/**
 * Collect all checked ADDM groups from "ADDM CMD Buttons" modal in checkboxes
 * @returns {[]}
 */
function addmGroupsSelected() {
    let checkedADDMs = [];
    let checkBoxes = document.getElementsByClassName("form-check-input");

    for (let checkbox of checkBoxes) {
        if (checkbox.checked) {
            if (checkedADDMs.includes(checkbox.value)) {
                console.log('Already selected');
                checkbox.checked = false;
            } else {
                checkedADDMs.push(checkbox.value);
                checkbox.checked = false;
            }
        }
    }
    console.log(checkedADDMs);
    return checkedADDMs;
}

/**
 * Collect all checked ADDM branches from "ADDM CMD Buttons" modal in checkboxes
 * @returns {[]}
 */
function addmBranchSelected() {
    let checkedADDMs = [];
    let checkBoxes = document.getElementsByClassName("addm-branch-checkbox");

    for (let checkbox of checkBoxes) {
        if (checkbox.checked) {
            if (checkedADDMs.includes(checkbox.value)) {
                console.log('Already selected');
                checkbox.checked = false;
            } else {
                checkedADDMs.push(checkbox.value);
                checkbox.checked = false;
            }
        }
    }
    console.log(checkedADDMs);
    return checkedADDMs;
}

/**
 * Generate command execution for selected ADDMs from modal addmCMDRun
 * @param event
 */
function addmCMDRunGenerate(event) {

    let runAddmCMD = event.currentTarget;
    let checkedADDMs = '';
    let checkedBranch = '';
    let selectedCMDs = '';

    checkedADDMs = addmGroupsSelected();
    checkedBranch = addmBranchSelected();
    selectedCMDs = addmCMDkeysSelected('addmCMDSelect');
    runAddmCMD.dataset.operation_key = 'addm_cmd_run';
    runAddmCMD.dataset.addm_group = checkedADDMs.join(',');
    runAddmCMD.dataset.command_key = selectedCMDs.join(',');
    runAddmCMD.dataset.addm_branch = checkedBranch.join(',');

    let toastBase = getToastDraft(runAddmCMD.dataset);
    let toastReady = fillToastBodyWithTaskDetails(runAddmCMD.dataset, toastBase);
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:

    RESTAdminOperationsPOST(runAddmCMD.dataset, toastReady);

    runAddmCMD.dataset.operation_key = '';
    runAddmCMD.dataset.addm_group = '';
    runAddmCMD.dataset.command_key = '';
    runAddmCMD.dataset.addm_branch = '';

    showToastTask(toastReady.id); // Make toast visible
    hideModal('addmCMDRun'); // Make toast visible
}


/**
 * MODAL functions, when modal is active opened
 */

/**
 * Show modal of each addm operations, call from ADDM table.
 */
$(document).ready(function () {
    $('#addmUIButtonsModal').on('show.bs.modal', function (event) {
        // let modal = document.getElementById("addmUIButtonsModal");
        // TODO: Change later to working example or not
        // let addmDetailsStr = document.getElementById("addm_details_str");
        // if (addmDetailsStr.firstElementChild) {
        //   addmDetailsStr.removeChild(addmDetailsStr.firstElementChild);
        // }

        let addmButtons = document.getElementsByClassName('addm-btn');
        let tableRow = getTableRowFromEvent(event);
        let addmHostRe = /(http:\/\/)(\S+)(\.bmc\.com)/;

        // let addm_p = document.createElement('p');  // toast-body
        // addm_p.innerText = `${tableRow.cells['addm_group'].textContent} | \
        // ${tableRow.cells['branch_lock'].textContent} | ${tableRow.cells['addm_name'].textContent} | \
        // ${tableRow.cells['addm_v_int'].textContent} | ${tableRow.cells['addm_host'].textContent} | \
        // ${tableRow.cells['addm_ip'].textContent}`;
        // addmDetailsStr.appendChild(addm_p);

        for (let btn of addmButtons) {
            let old_href = btn.href;
            btn.href = old_href.replace(addmHostRe, `$1${tableRow.cells['addm_host'].textContent}$3`);
        }
    });
});

/**
 * Modal for addmCleanupButtons
 * Render Toast when task fired
 */
$(document).ready(function () {
    $('#addmCleanupButtons').on('show.bs.modal', function (event) {
        let modal = document.getElementById("addmCleanupButtons");
        let addmButtons = modal.getElementsByClassName('addm-btn');
        for (let btn of addmButtons) {
            btn.dataset.operation_key = 'addm_cleanup';
            btn.modalId = 'addmCleanupButtons';
            btn.removeEventListener('click', buttonActivationADDM);
            btn.addEventListener("click", buttonActivationADDM);
        }
    });
});

/**
 * Modal for addmCMDRun
 * Render Toast when task fired
 */
$(document).ready(function () {
    $('#addmCMDRun').on('show.bs.modal', function (event) {
        let modal = document.getElementById("addmCMDRun");
        console.log("Working on addmCMDRun modal!");
        let runAddmCMD = document.getElementById("runAddmCMD");
        // if previous exec
        runAddmCMD.removeEventListener('click', addmCMDRunGenerate);
        runAddmCMD.addEventListener("click", addmCMDRunGenerate);

    });
});

/**
 * Modal for addmServiceButtonsModal
 * Render Toast when task fired
 */
$(document).ready(function () {
    $('#addmServiceButtonsModal').on('show.bs.modal', function (event) {
        console.log("Working on addmServiceButtonsModal modal!");
        let relTableRow = event.relatedTarget.parentNode.parentNode;
        console.log(relTableRow.cells['addm_host'].textContent);
        let runSingleAddmCMD = document.getElementById("runSingleAddmCMD");
        runSingleAddmCMD.addEventListener("click", function (event) {
            let selectedCMDs = addmCMDkeysSelected('addmSingleCMDSelect');
            runSingleAddmCMD.dataset.operation_key = 'addm_cmd_run';
            runSingleAddmCMD.dataset.addm_host = relTableRow.cells['addm_host'].textContent;
            runSingleAddmCMD.dataset.command_key = selectedCMDs.join(',');
            console.log(runSingleAddmCMD.dataset);

            let toastBase = getToastDraft(runSingleAddmCMD.dataset);
            let toastReady = fillToastBodyWithTaskDetails(runSingleAddmCMD.dataset, toastBase);
            appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:

            RESTAdminOperationsPOST(runSingleAddmCMD.dataset, toastReady);
            showToastTask(toastReady.id); // Make toast visible
            hideModal('addmServiceButtonsModal'); // Make toast visible
        });

    });
});

/**
 * Modal for addmSYNCButtons
 * Render Toast when task fired
 */
$(document).ready(function () {
    $('#addmSYNCButtons').on('show.bs.modal', function (event) {
        let modal = document.getElementById("addmSYNCButtons");
        let addmButtons = modal.getElementsByClassName('addm-btn');
        for (let btn of addmButtons) {
            btn.dataset.operation_key = 'addm_sync_shares';
            btn.modalId = 'addmSYNCButtons';
            btn.removeEventListener('click', buttonActivationADDM);
            btn.addEventListener("click", buttonActivationADDM);
        }
    });
});
