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
function addmCMDKeysSelected(elementId) {
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
    if (selectedCMDs.length) {
        console.log(`selectedCMDs: ${selectedCMDs}`);
    }
    else {
        console.log("No CMD were selected, this could be a wrong operation!")
    }
    return selectedCMDs;
}

/**
 * Collect all checked ADDM groups from "ADDM CMD Buttons" modal in checkboxes
 * @returns {[]}
 */
function addmGroupsSelected() {
    let checkedADDMs = [];
    let checkBoxes = document.getElementsByClassName("addm-group-checkbox");

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
    if (checkedADDMs.length) {
        console.log(`checkedADDMs: ${checkedADDMs}`);
    }
    return checkedADDMs;
}

/**
 * Collect all checked ADDM branches from "ADDM CMD Buttons" modal in checkboxes
 * @returns {[]}
 */
function addmBranchSelected() {
    let addmBranchSelected = [];
    let checkBoxes = document.getElementsByClassName("addm-branch-checkbox");

    for (let checkbox of checkBoxes) {
        if (checkbox.checked) {
            if (addmBranchSelected.includes(checkbox.value)) {
                console.log('Already selected');
                checkbox.checked = false;
            } else {
                addmBranchSelected.push(checkbox.value);
                checkbox.checked = false;
            }
        }
    }
    if (addmBranchSelected.length) {
        console.log(`addmBranchSelected ${addmBranchSelected}`);
    }
    return addmBranchSelected;
}

/**
 * Generate command execution for selected ADDMs from modal addmCMDRun
 * @param event
 */
function addmCMDRunGenerate(event) {
    let runAddmCMD = event.currentTarget;

    let checkedADDMs = [];
    let checkedBranch = [];
    let selectedCMDs = [];

    checkedADDMs = addmGroupsSelected();
    checkedBranch = addmBranchSelected();

    if (runAddmCMD.dataset.selectId) {
        console.log(`Collect addm commands from multiple selector form selectId: ${runAddmCMD.dataset.selectId}`);
        // Collect addm commands from multiple selector form.
        selectedCMDs = addmCMDKeysSelected(runAddmCMD.dataset.selectId);
        runAddmCMD.dataset.command_key = selectedCMDs.join(',');
        delete runAddmCMD.dataset.selectId;
    }

    if (runAddmCMD.dataset.operation_key) {
        // on addm_cleanup use key addm_cleanup from btn data (addm_sync_shares, addm_sync_utils)
        console.log("Leave current operation_key from btn: " + runAddmCMD.dataset.operation_key)
    } else {
        // Other operations use default if above is false
        runAddmCMD.dataset.operation_key = 'addm_cmd_run';
    }

    runAddmCMD.dataset.addm_group = checkedADDMs.join(',');
    runAddmCMD.dataset.addm_branch = checkedBranch.join(',');

    let toastBase = getToastDraft(runAddmCMD.dataset);
    let toastReady = fillToastBodyWithTaskDetails(runAddmCMD.dataset, toastBase);

    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    RESTAdminOperationsPOST(runAddmCMD.dataset, toastReady);

    console.log("Toast ID to show: " + toastBase.id);
    delete runAddmCMD.dataset;

    $('#' + toastBase.id).toast('show');
    $('.show').modal('hide');
}


/**
 * MODAL functions, when modal is active opened
 */

/**
 * Show modal of each addm operations, call from ADDM table.
 */
$(document).ready(function () {
    $('#addmUIButtonsModal').on('show.bs.modal', function (event) {
        // console.log(addm_dev_json);
        let modalBtn = event.relatedTarget;
        let addmButtons = document.getElementsByClassName('addm-btn');
        let addmHostRe = /(http:\/\/)(\S+)(\.bmc\.com)/;
        for (let btn of addmButtons) {
            let old_href = btn.href;
            btn.href = old_href.replace(addmHostRe, `$1${modalBtn.dataset['addm_host']}$3`);
        }
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

        let runSingleAddmCMD = document.getElementById("runSingleAddmCMD");
        let runAddmCleanup = document.getElementById("single_addm_cleanup");
        let runAddmSyncShares = document.getElementById("single_addm_sync_shares");
        let runAddmSyncUtils = document.getElementById("single_addm_sync_utils");

        runSingleAddmCMD.dataset.addm_host = relTableRow.cells['addm_host'].textContent;
        runAddmCleanup.dataset.addm_host = relTableRow.cells['addm_host'].textContent;
        runAddmSyncShares.dataset.addm_host = relTableRow.cells['addm_host'].textContent;
        runAddmSyncUtils.dataset.addm_host = relTableRow.cells['addm_host'].textContent;
        runAddmCleanup.dataset.operation_key = 'addm_cleanup';
        runAddmSyncShares.dataset.operation_key = 'addm_sync_shares';
        runAddmSyncUtils.dataset.operation_key = 'addm_sync_utils';
        runSingleAddmCMD.dataset.selectId = 'addmSingleCMDSelect';

        // if previous exec
        runSingleAddmCMD.removeEventListener('click', addmCMDRunGenerate);
        runAddmCleanup.removeEventListener('click', addmCMDRunGenerate);
        runAddmSyncShares.removeEventListener('click', addmCMDRunGenerate);
        runAddmSyncUtils.removeEventListener('click', addmCMDRunGenerate);

        runSingleAddmCMD.addEventListener("click", addmCMDRunGenerate);
        runAddmCleanup.addEventListener("click", addmCMDRunGenerate);
        runAddmSyncShares.addEventListener("click", addmCMDRunGenerate);
        runAddmSyncUtils.addEventListener("click", addmCMDRunGenerate);

    });
});

/**
 * Modal for addmCleanupButtons
 * Render Toast when task fired
 */
$(document).ready(function () {
    $('#addmCleanupButtons').on('show.bs.modal', function (event) {
        console.log("Working on addmCleanupButtons modal!");
        let runADDMCleanup = document.getElementById("runADDMCleanup");
        // if previous exec
        runADDMCleanup.removeEventListener('click', addmCMDRunGenerate);
        runADDMCleanup.addEventListener("click", addmCMDRunGenerate);

    });
});

/**
 * Modal for addmCMDRun
 * Render Toast when task fired
 */
$(document).ready(function () {
    $('#addmCMDRun').on('show.bs.modal', function (event) {
        console.log("Working on addmCMDRun modal!");
        let runAddmCMD = document.getElementById("runAddmCMD");
        runAddmCMD.dataset.selectId = 'addmCMDSelect';
        // if previous exec
        runAddmCMD.removeEventListener('click', addmCMDRunGenerate);
        runAddmCMD.addEventListener("click", addmCMDRunGenerate);

    });
});

/**
 * Modal for addmSYNCButtons
 * Render Toast when task fired
 */
$(document).ready(function () {
    $('#addmSYNCButtons').on('show.bs.modal', function (event) {
        console.log("Working on addmCMDRun modal!");
        let runADDMRsyncTests = document.getElementById("runADDMRsyncTests");
        let runADDMRsyncUtils = document.getElementById("runADDMRsyncUtils");

        // if previous exec
        runADDMRsyncTests.removeEventListener('click', addmCMDRunGenerate);
        runADDMRsyncUtils.removeEventListener('click', addmCMDRunGenerate);

        runADDMRsyncTests.addEventListener("click", addmCMDRunGenerate);
        runADDMRsyncUtils.addEventListener("click", addmCMDRunGenerate);
    });
});
