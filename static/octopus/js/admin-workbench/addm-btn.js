$(document).ready(function () {
    $('#addmButtonsModal').on('hidden.bs.modal', function (event) {
        $('#addmButtonsModal').modal('hide');
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

/**
 * Show modal of each addm operations, call from ADDM table.
 */
$(document).ready(function () {
    $('#addmButtonsModal').on('show.bs.modal', function (event) {
        // let modal = document.getElementById("addmButtonsModal");
        let addmDetailsStr = document.getElementById("addm_details_str");
        let addmButtons = document.getElementsByClassName('addm-btn');
        let tableRow = getTableRowFromEvent(event);
        let addmHostRe = /(http:\/\/)(\S+)(\.bmc\.com)/;
        addmDetailsStr.innerText = `${tableRow.cells['addm_group'].textContent} | \
        ${tableRow.cells['branch_lock'].textContent} | ${tableRow.cells['addm_name'].textContent} | \ 
        ${tableRow.cells['addm_v_int'].textContent} | ${tableRow.cells['addm_host'].textContent} | \
        ${tableRow.cells['addm_ip'].textContent}`;
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
            btn.removeEventListener('click', buttonActivation);
            btn.addEventListener("click", buttonActivation);
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
        let addmButtons = modal.getElementsByClassName('addm-btn');
        for (let btn of addmButtons) {
            btn.dataset.operation_key = 'addm_cmd_run';
            btn.modalId = 'addmCMDRun';
            btn.removeEventListener('click', buttonActivation);
            btn.addEventListener("click", buttonActivation);
        }
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
            btn.removeEventListener('click', buttonActivation);
            btn.addEventListener("click", buttonActivation);
        }
    });
});

/**
 * Post admin task for addm operations.
 * Show toast with selected task, addm name ot group and operation key and args
 * Later get task id, wait, show toast task response.
 * @param btnDataset
 * @param toastReady
 * @returns {*}
 */
function AdminOperationsADDM(btnDataset, toastReady) {
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

function buttonActivation(event) {
    let btn = event.currentTarget;
    let toastBase = getToastDraft(btn.dataset);
    let toastReady = fillToastBodyWithTaskDetails(btn.dataset, toastBase);
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    AdminOperationsADDM(btn.dataset, toastReady);
    showToastTask(btn.modalId, toastReady.id); // Make toast visible
}