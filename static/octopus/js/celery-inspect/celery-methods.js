/**
 *
 **/



function eventListenerCeleryTabs(funcToRun) {
    let nav_active_reserved_tab = document.getElementById("nav-active-reserved-tab");
    let nav_active_tab = document.getElementById("nav-active-tab");
    let nav_reserved_tab = document.getElementById("nav-reserved-tab");
    let nav_scheduled_tab = document.getElementById("nav-scheduled-tab");
    let nav_registered_tab = document.getElementById("nav-registered-tab");

    nav_active_reserved_tab.addEventListener("click", function () {
        // data-workers="{{ worker }}"
        // data-operation_key="tasks_get_active_reserved"
        funcToRun(nav_active_reserved_tab.dataset)
    });
    nav_active_tab.addEventListener("click", function () {
        // data-workers="{{ worker }}"
        // data-operation_key="tasks_get_active"
        funcToRun(nav_active_tab.dataset)
    });
    nav_reserved_tab.addEventListener("click", function () {
        // data-workers="{{ worker }}"
        // data-operation_key="tasks_get_reserved"
        funcToRun(nav_reserved_tab.dataset)
    });
    nav_scheduled_tab.addEventListener("click", function () {
        // data-workers="{{ worker }}"
        // data-operation_key="tasks_get_scheduled"
        funcToRun(nav_scheduled_tab.dataset)
    });
    nav_registered_tab.addEventListener("click", function () {
        // data-workers="{{ worker }}"
        // data-operation_key="tasks_get_registered"
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

function prepareTabContent(tabId) {
    let tab = document.getElementById(tabId);
    let p = document.createElement('p');
    // Clear any older nodes:
    tab.querySelectorAll('*').forEach(n => n.remove());
    if (tabId === "active") {
        p.innerText = 'Active tasks';
    }
    else if (tabId === "reserved") {
        p.innerText = 'Reserved tasks';
    }
    else if (tabId === "active-reserved") {
        p.innerText = 'Active & reserved tasks';
    }
    else if (tabId === "scheduled") {
        p.innerText = 'Scheduled tasks';
    }
    else if (tabId === "registered") {
        p.innerText = 'Registered tasks';
    }
    tab.appendChild(p);

}

function fillTabTaskTableActRes(tabNode, worker_card, RESTResult) {
    // If REST request failed - probably celery worker just go somewhere - show warning:
    if (!RESTResult.response) {
        console.log("Workers are probably irresponsible, cannot get all tasks!");
        let workerCardBase = worker_card.children[0].cloneNode(true);
        let cardHeader = workerCardBase.childNodes[1];  // Header
        let cardBody = workerCardBase.childNodes[3];  // Body
        cardHeader.innerText = `Worker cannot be inspected`;
        cardBody.innerText = `Celery workers could become irresponsible, so Django cannot inspect them. 
    It does not mean tasks are not running, we only cannot inspect them.
    Please restart Django App and Celery workers or ask Admin for support.`;
        tabNode.appendChild(workerCardBase);
    }

    let argsShow = ['id', 'name', 'args', 'time_start', 'type'];

    let activeTasks = RESTResult.response['active'];  // Iter over workers from this array
    let reservedTasks = RESTResult.response['reserved'];  // Call by worker key from iter of above

    for (let [w_key, _] of Object.entries(activeTasks)) {
        let w_tasks = activeTasks[w_key];  // Having the same logic for both. Get by worker key
        let w_reserved = reservedTasks[w_key];  // Having the same logic for both. Get by worker key
        let workerCardBase = worker_card.children[0].cloneNode(true);  // Clone card for all workers, even if empty
        let cardHeader = workerCardBase.childNodes[1];  // Header - add worker key
        let cardBody = workerCardBase.childNodes[3];  // Body - copy/add table of tasks
        let cardFooter = workerCardBase.childNodes[5];  // Footer - add worker buttons
        let taskTableBody = cardBody.firstElementChild.tBodies[0];  // Task table

        // Set card header span as worker key:
        cardHeader.childNodes[0].innerText = `${w_key}`;  // Card header span


        if (w_tasks && w_tasks.length) {
            taskTableFillRow(w_tasks, argsShow, taskTableBody);
        }
        if (w_reserved && w_reserved.length) {
            taskTableFillRow(w_reserved, argsShow, taskTableBody);
        }
        if (!(w_tasks && w_tasks.length) && !(w_reserved && w_reserved.length)) {
            cardBody.firstElementChild.remove();
            cardBody.innerText = 'Queue is empty';
            tabNode.appendChild(workerCardBase)
        } else {
            // Append table of tasks only if there are tasks
            tabNode.appendChild(workerCardBase);
            // Worker buttons:
            workerButtonsAssign(w_key, cardFooter);
        }
    }
}

function workerButtonsAssign(w_key, cardFooter) {
    let worker = w_key.split("@")[0];
    let worker_buttons = [
        {"operation_key": "task_revoke_active", "description" : "Revoke active", "worker": worker, "color": "badge-warning"},
        {"operation_key": "task_revoke_reserved", "description" : "Revoke reserved", "worker": worker, "color": "badge-warning"},
        {"operation_key": "task_revoke_active_reserved", "description" : "Revoke a/r", "worker": worker, "color": "badge-danger"},
        {"operation_key": "worker_ping", "description" : "Ping worker", "worker": worker, "color": "badge-success"},
        {"operation_key": "worker_heartbeat", "description" : "Worker heartbeat", "worker": worker, "color": "badge-secondary"},
    ];
    for (let button_set of worker_buttons) {
        let btn = document.createElement('a');
        btn.setAttribute("class", `badge ${button_set["color"]} ${button_set["operation_key"]}`);
        btn.dataset.operation_key = button_set["operation_key"];
        btn.dataset.worker = button_set["worker"];
        btn.innerText = button_set["description"];
        cardFooter.appendChild(btn);
        //TODO: Add event listener -> call RESTCeleryTaskPOST -> Show toast confirmation
        btn.addEventListener("click", function () {
            RESTCeleryTaskPOST(btn.dataset, drawToastConfirm)
        });
    }
}

function taskTableFillRow(tasksObj, argsShow, taskTableBody) {
    for (let task of tasksObj) {
        let task_row = document.createElement('tr');
        for (let [t_key, t_val] of Object.entries(task)) {
            if (argsShow.includes(t_key)) {
                let key_td = document.createElement('td');
                key_td.innerText = `${t_val}`;
                task_row.appendChild(key_td);
            }
            taskTableBody.appendChild(task_row);
        }
        // Assign revoke button for each task obj in row:
        taskTableRowActionsButton(task, task_row);
    }
}

function taskTableRowActionsButton(task, task_row) {
    // Extra td for Actions:
    let actions_td = document.createElement('td');
    let actions_btn = document.createElement('a');
    actions_btn.setAttribute("class", "badge badge-warning revoke-task-by-id");
    actions_btn.dataset.operation_key = 'task_revoke_by_id';
    actions_btn.dataset.task_id = task['id'];
    actions_btn.innerText = 'Revoke';
    actions_td.appendChild(actions_btn);
    task_row.appendChild(actions_td);
    //TODO: Add event listener -> call RESTCeleryTaskPOST -> Show toast confirmation
    actions_btn.addEventListener("click", function () {
            RESTCeleryTaskPOST(actions_btn.dataset, drawToastConfirm)
        });
}

function fillTabTaskTable(tabNode, worker_card, RESTResult) {
    let argsShow = ['id', 'name', 'args', 'time_start', 'type'];
    // let tasks = unpackActiveReserved(RESTResult.response);

    if (RESTResult.response) {
        for (const [w_key, w_value] of Object.entries(RESTResult.response)) {

            let workerCardBase = worker_card.children[0].cloneNode(true);
            let cardHeader = workerCardBase.childNodes[1];  // Header
            let cardBody = workerCardBase.childNodes[3];  // Body

            cardHeader.childNodes[0].innerText = `${w_key}`;  // worker name
            workerButtons(workerCardBase, w_key);

            if (w_value && w_value.length > 0) {
                let taskTableBody = cardBody.firstElementChild.tBodies[0];  // Task table
                for (let task of w_value) {
                    let task_row = document.createElement('tr');
                    for (const [key, val] of Object.entries(task)) {
                        if (argsShow.includes(key)) {
                            let key_td = document.createElement('td');
                            key_td.innerText = `${val}`;
                            task_row.appendChild(key_td);
                        }
                        taskTableBody.appendChild(task_row);
                    }
                    // Extra td for Actions:
                    let actions_td = document.createElement('td');
                    let actions_btn = document.createElement('a');
                    actions_btn.setAttribute("class", "badge badge-warning revoke-task-by-id");
                    actions_btn.dataset.task_id = task['id'];
                    actions_btn.innerText = 'Revoke';
                    actions_td.appendChild(actions_btn);
                    task_row.appendChild(actions_td);
                }
            } else {
                cardBody.firstElementChild.remove();
                cardBody.innerText = 'Queue is empty.'
            }
            tabNode.appendChild(workerCardBase)
        }
        // Assign listeners for task operations:
        eventListenerRevokeBtn(taskOperationsButtonsToast);
    } else {
        console.log("Workers are probably irresponsible, cannot get all tasks!");
        let workerCardBase = worker_card.children[0].cloneNode(true);
        let cardHeader = workerCardBase.childNodes[1];  // Header
        let cardBody = workerCardBase.childNodes[3];  // Body
        cardHeader.innerText = `Worker cannot be inspected`;
        cardBody.innerText = `Celery workers could become irresponsible, so Django cannot inspect them. 
    It does not mean tasks are not running, we only cannot inspect them.
    Please restart Django App and Celery workers or ask Admin for support.`;
        tabNode.appendChild(workerCardBase);
    }
}


/**
 * @return {string}
 */
function RESTCeleryTaskPOST(tabsDataset, nextFunc) {
    console.log("RESTCeleryTaskPOST RUN:");
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


function drawToastConfirm(tabsDataset, result) {
    // Draw toast with confirmation
    console.log("drawToastConfirm");
    console.log(tabsDataset);
    console.log(result);
}