/**
 *
 **/



function eventListenerCeleryTabs(funcToRun) {
    let nav_active_tab = document.getElementById("nav-active-tab");
    let nav_reserved_tab = document.getElementById("nav-reserved-tab");
    let nav_active_reserved_tab = document.getElementById("nav-active-reserved-tab");
    let nav_scheduled_tab = document.getElementById("nav-scheduled-tab");
    let nav_registered_tab = document.getElementById("nav-registered-tab");

    nav_active_tab.addEventListener("click", function () {
        funcToRun(nav_active_tab.dataset)
    });
    nav_reserved_tab.addEventListener("click", function () {
        funcToRun(nav_reserved_tab.dataset)
    });
    nav_active_reserved_tab.addEventListener("click", function () {
        funcToRun(nav_active_reserved_tab.dataset)
    });
    nav_scheduled_tab.addEventListener("click", function () {
        funcToRun(nav_scheduled_tab.dataset)
    });
    nav_registered_tab.addEventListener("click", function () {
        funcToRun(nav_registered_tab.dataset)
    });
}

function eventListenerRevokeBtn(funcToRun) {
    let revokeActiveTasks = document.getElementById("revoke-active-tasks");
    let revokeReservedTasks = document.getElementById("revoke-reserved-tasks");
    let revokeAllTasks = document.getElementById("revoke-all-tasks");
    let discardAllTasks = document.getElementById("discard-all-tasks");
    let purgeAllTasks = document.getElementById("purge-all-tasks");

    revokeActiveTasks.addEventListener("click", function () {
        revokeActiveTasks.dataset.operation_key = 'task_revoke_active';
        funcToRun(revokeActiveTasks.dataset)
    });
    revokeReservedTasks.addEventListener("click", function () {
        revokeReservedTasks.dataset.operation_key = 'task_revoke_reserved';
        funcToRun(revokeReservedTasks.dataset)
    });
    revokeAllTasks.addEventListener("click", function () {
        revokeAllTasks.dataset.operation_key = 'task_revoke_active_reserved';
        funcToRun(revokeAllTasks.dataset)
    });
    discardAllTasks.addEventListener("click", function () {
        discardAllTasks.dataset.operation_key = 'task_discard_all';
        funcToRun(discardAllTasks.dataset)
    });
    purgeAllTasks.addEventListener("click", function () {
        purgeAllTasks.dataset.operation_key = 'task_purge_all';
        funcToRun(purgeAllTasks.dataset)
    });

    let revokeTaskById = document.getElementsByClassName('revoke-task-by-id');
    for (let revokeBtn of revokeTaskById) {
        revokeBtn.addEventListener("click", function () {
        revokeBtn.dataset.operation_key = 'task_revoke_by_id';
        funcToRun(revokeBtn.dataset)
    });
    }
}

function workerButtons(workerCardBase, w_key) {
    let workerButtons = workerCardBase.getElementsByClassName('worker-buttons')[0];

    let activeTasksWorker = document.createElement("a");
    let reservedTasksWorker = document.createElement("a");
    let pingCurrentWorker = document.createElement("a");
    let heartbeatCurrentWorker = document.createElement("a");
    let revokeSingleTask = document.createElement("a");

    activeTasksWorker.setAttribute("id", "active-tasks-worker-" + w_key);
    reservedTasksWorker.setAttribute("id", "reserved-tasks-worker-" + w_key);
    pingCurrentWorker.setAttribute("id", "ping-current-worker-" + w_key);
    heartbeatCurrentWorker.setAttribute("id", "heartbeat-current-worker-" + w_key);
    revokeSingleTask.setAttribute("id", "revoke-single-task-" + w_key);

    activeTasksWorker.setAttribute("class", "badge badge-info");
    reservedTasksWorker.setAttribute("class", "badge badge-info");
    pingCurrentWorker.setAttribute("class", "badge badge-success");
    heartbeatCurrentWorker.setAttribute("class", "badge badge-success");
    revokeSingleTask.setAttribute("class", "badge badge-warning");

    activeTasksWorker.href = `/octo_admin/celery_inspect/?worker=${w_key.split('@')[0]}`;
    reservedTasksWorker.href = `/octo_admin/celery_inspect/?worker=${w_key.split('@')[0]}`;
    pingCurrentWorker.href = `/octo_admin/celery_inspect/?worker=${w_key.split('@')[0]}`;
    heartbeatCurrentWorker.href = `/octo_admin/celery_inspect/?worker=${w_key.split('@')[0]}`;
    revokeSingleTask.href = `/octo_admin/celery_inspect/?worker=${w_key.split('@')[0]}`;

    activeTasksWorker.innerText = 'Active tasks';
    reservedTasksWorker.innerText = 'Reserved tasks';
    pingCurrentWorker.innerText = 'Ping worker';
    heartbeatCurrentWorker.innerText = 'Heartbeat worker';
    revokeSingleTask.innerText = 'Revoke tasks';

    workerButtons.appendChild(activeTasksWorker);
    workerButtons.appendChild(reservedTasksWorker);
    workerButtons.appendChild(pingCurrentWorker);
    workerButtons.appendChild(heartbeatCurrentWorker);
    workerButtons.appendChild(revokeSingleTask);

}

/**
 * @return {string}
 */
function RESTCeleryTaskPOST(tabsDataset, nextFunc) {
    console.log("REST RUN:");
    console.log(tabsDataset);
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/x-www-form-urlencoded",
        url: '/octo_admin/task_operation/',
        data: tabsDataset,
        "beforeSend": function (xhr, settings) {
            $.ajaxSettings.beforeSend(xhr, settings)
        },
        "success": function (result) {
            console.log(`POST result: ${result}`);
            if (result) {
                nextFunc(tabsDataset, result)
            } else {
                console.log("Task POST send, but haven't been added. No task_id in result!")
            }
        },
        "error": function () {
            console.log("POST TASK ERROR, something goes wrong...")
        },
    });
    return 'testButtonDataset';
}