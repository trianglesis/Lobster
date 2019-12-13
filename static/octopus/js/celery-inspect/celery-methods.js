/**
 *
 **/

function eventListenerCeleryMainButtons(funcToRun) {
    let revokeActiveTasks = document.getElementById("revoke-active-tasks");
    let revokeReservedTasks = document.getElementById("revoke-reserved-tasks");
    let revokeAllTasks = document.getElementById("revoke-all-tasks");
    revokeActiveTasks.addEventListener("click", function () {
        revokeActiveTasks.dataset.operation_key="task_revoke_active";
        RESTCeleryTaskPOST(revokeActiveTasks.dataset, workerButtonsDrawToastConfirm)
    });
    revokeReservedTasks.addEventListener("click", function () {
        revokeReservedTasks.dataset.operation_key="task_revoke_reserved";
        RESTCeleryTaskPOST(revokeReservedTasks.dataset, workerButtonsDrawToastConfirm)
    });
    revokeAllTasks.addEventListener("click", function () {
        revokeAllTasks.dataset.operation_key="task_revoke_active_reserved";
        RESTCeleryTaskPOST(revokeAllTasks.dataset, workerButtonsDrawToastConfirm)
    });
}

/**
 *
 * @param funcToRun
 */
function eventListenerCeleryTabs(funcToRun) {
    let navActiveReservedTab = document.getElementById("nav-active-reserved-tab");
    // let navActiveTab = document.getElementById("nav-active-tab");
    // let navReservedTab = document.getElementById("nav-reserved-tab");
    // let navScheduledTab = document.getElementById("nav-scheduled-tab");
    let navRegisteredTab = document.getElementById("nav-registered-tab");

    navActiveReservedTab.addEventListener("click", function () {
        // data-workers="{{ worker }}"
        // data-operation_key="tasks_get_active_reserved"
        funcToRun(navActiveReservedTab.dataset)
    });
    // navActiveTab.addEventListener("click", function () {
    //     // data-workers="{{ worker }}"
    //     // data-operation_key="tasks_get_active"
    //     funcToRun(navActiveTab.dataset)
    // });
    // navReservedTab.addEventListener("click", function () {
    //     // data-workers="{{ worker }}"
    //     // data-operation_key="tasks_get_reserved"
    //     funcToRun(navReservedTab.dataset)
    // });
/*    navScheduledTab.addEventListener("click", function () {
        // data-workers="{{ worker }}"
        // data-operation_key="tasks_get_scheduled"
        funcToRun(navScheduledTab.dataset)
    });*/
    navRegisteredTab.addEventListener("click", function () {
        // data-workers="{{ worker }}"
        // data-operation_key="tasks_get_registered"
        funcToRun(navRegisteredTab.dataset)
    });
}

/**
 *
 * @param tabId
 */
function prepareTabContent(tabId) {
    let tab = document.getElementById(tabId);
    let p = document.createElement('p');
    // Clear any older nodes:
    tab.querySelectorAll('*').forEach(n => n.remove());
    if (tabId === "active") {
        p.innerText = 'Active tasks';
    } else if (tabId === "reserved") {
        p.innerText = 'Reserved tasks';
    } else if (tabId === "active-reserved") {
        p.innerText = 'Active & reserved tasks';
    } else if (tabId === "scheduled") {
        p.innerText = 'Scheduled tasks';
    } else if (tabId === "registered") {
        p.innerText = 'Registered tasks';
    }
    tab.appendChild(p);

}

/**
 *
 * @param tabNode
 * @param worker_card
 * @param RESTResult
 */
function fillTabTaskTableActRes(tabNode, worker_card, RESTResult) {
    let activeTasks = RESTResult.response['active'];  // Iter over workers from this array
    let reservedTasks = RESTResult.response['reserved'];  // Call by worker key from iter of above
    // If REST request failed - probably celery worker just go somewhere - show warning:
    console.log(`fillTabTaskTableActRes:`, RESTResult.response);

    if (!activeTasks && !reservedTasks) {
        console.log("Workers are probably irresponsible, cannot get all tasks!");
        let workerCardBase = worker_card.children[0].cloneNode(true);
        let cardHeader = workerCardBase.childNodes[1];  // Header
        let cardBody = workerCardBase.childNodes[3];  // Body
        cardHeader.innerText = `Worker cannot be inspected`;
        cardBody.innerText = `Celery workers could become irresponsible, so Django cannot inspect them. 
    It does not mean tasks are not running, we only cannot inspect them.
    Please restart Django App and Celery workers or ask Admin for support.`;
        tabNode.appendChild(workerCardBase);
    } else {
        let argsShow = ['id', 'name', 'args', 'kwargs', 'time_start', 'type'];
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
                let span = document.createElement('span');
                span.innerText = 'Queue is empty';
                cardHeader.appendChild(span);
                tabNode.appendChild(workerCardBase);
                cardBody.remove();
                cardFooter.remove();
            } else {
                // Append table of tasks only if there are tasks
                tabNode.appendChild(workerCardBase);
                // Worker buttons:
                workerButtonsAssign(w_key, cardFooter);
            }
        }
    }
}

function fillScheduledRegisteredTasks(tabNode, worker_card, RESTResult) {
    let scheduled = RESTResult.response['scheduled'];  // Iter over workers from this array
    let registered = RESTResult.response['registered'];  // Call by worker key from iter of above
    console.log(`fillScheduledRegisteredTasks:`, RESTResult.response);

    if (scheduled) {
        for (let [w_key, _] of Object.entries(scheduled)) {
            let workerCardBase = worker_card.children[0].cloneNode(true);  // Clone card for all workers, even if empty
            let w_tasks = scheduled[w_key];  // Having the same logic for both. Get by worker key
            let cardHeader = workerCardBase.childNodes[1];  // Header - add worker key
            let cardBody = workerCardBase.childNodes[3];  // Body - copy/add table of tasks
            let taskTableBody = cardBody.firstElementChild.tBodies[0];  // Task table
            // Set card header span as worker key:
            cardHeader.childNodes[0].innerText = `${w_key}`;  // Card header span
            if (w_tasks && w_tasks.length) {
            }
            tabNode.appendChild(workerCardBase);
        }

    } else if (registered) {
        for (let [w_key, _] of Object.entries(registered)) {
            let workerCardBase = worker_card.children[0].cloneNode(true);  // Clone card for all workers, even if empty
            let w_tasks = registered[w_key];  // Having the same logic for both. Get by worker key
            let cardHeader = workerCardBase.childNodes[1];  // Header - add worker key
            let cardBody = workerCardBase.childNodes[3];  // Body - copy/add table of tasks
            let taskTableBody = cardBody.firstElementChild.remove();  // Task table
            // Set card header span as worker key:
            cardHeader.childNodes[0].innerText = `${w_key}`;  // Card header span
            if (w_tasks && w_tasks.length) {
                taskRegisteredTableFillRow(w_tasks, cardBody);
            }
            tabNode.appendChild(workerCardBase);
        }

    }
}

/**
 *
 * @param w_key
 * @param cardFooter
 */
function workerButtonsAssign(w_key, cardFooter) {
    let worker = w_key.split("@")[0];
    let worker_buttons = [
        {
            "operation_key": "task_revoke_active",
            "description": "Revoke active",
            "workers": worker,
            "color": "badge-warning"
        },
        {
            "operation_key": "task_revoke_reserved",
            "description": "Revoke reserved",
            "workers": worker,
            "color": "badge-warning"
        },
        {
            "operation_key": "task_revoke_active_reserved",
            "description": "Revoke a/r",
            "workers": worker,
            "color": "badge-danger"
        },
        {
            "operation_key": "worker_ping",
            "description": "Ping worker",
            "workers": worker,
            "color": "badge-success"
        },
        {
            "operation_key": "worker_heartbeat",
            "description": "Worker heartbeat",
            "workers": worker,
            "color": "badge-secondary"
        },
    ];
    let btnDiv = document.createElement('div');
    btnDiv.setAttribute('class', 'worker-card-buttons');
    btnDiv.style.display = 'flex';
    btnDiv.style.justifyContent = 'space-between';
    for (let button_set of worker_buttons) {
        let btn = document.createElement('a');
        btn.setAttribute("class", `btn btn-sm ${button_set["color"]} ${button_set["operation_key"]}`);
        btn.dataset.operation_key = button_set["operation_key"];
        btn.dataset.workers = button_set["workers"];
        btn.innerText = button_set["description"];
        btnDiv.appendChild(btn);

        // Event listener for worker buttons  - in footer of worker card.
        btn.addEventListener("click", function () {
            RESTCeleryTaskPOST(btn.dataset, workerButtonsDrawToastConfirm)
        });
    }
    cardFooter.appendChild(btnDiv);
}

/**
 *
 * @param tasksObj
 * @param argsShow
 * @param taskTableBody
 */
function taskTableFillRow(tasksObj, argsShow, taskTableBody) {
    for (let task of tasksObj) {
        let task_row = document.createElement('tr');
        for (let [t_key, t_val] of Object.entries(task)) {
            if (argsShow.includes(t_key)) {
                let key_td = document.createElement('td');
                key_td.setAttribute('class', `td-task-${t_key}`);

                // Task ARGS
                if (t_key === 'args') {
                    if (t_val[0]) {
                        key_td.innerText = `${t_val[0].split(';').join('\n')}`;
                    } else {
                        key_td.innerText = `${t_val}`;
                    }

                // Task NAME and TYPE
                } else if (t_key === 'name' || t_key === 'type') {
                    if (t_val[0]) {
                        key_td.innerText = `${t_val[0].split('.').join('\n')}`;
                    } else {
                        key_td.innerText = `${t_val}`;
                    }

                // Task KWARGS
                } else if (t_key === 'kwargs') {
                    if (t_val['test_item']) {
                        key_td.innerText = `branch: ${t_val['test_item']['tkn_branch']
                        }\nLibrary :${t_val['test_item']['pattern_library']
                        }\nDir: ${t_val['test_item']['pattern_folder_name']
                        }\nt: ${t_val['test_item']['test_time_weight']}`;
                    }
                } else {
                    key_td.innerText = `${t_val}`;
                }
                task_row.appendChild(key_td);
            }
            taskTableBody.appendChild(task_row);
        }
        // Assign revoke button for each task obj in row:
        taskTableRowActionsButton(task, task_row);
    }
}

function taskRegisteredTableFillRow(tasksObj, taskTableBody) {
    for (let [id, task] of Object.entries(tasksObj)) {
        let task_row = document.createElement('tr');
        let int_td = document.createElement('td');
        let key_td = document.createElement('td');
        int_td.innerText = `${id}`;
        key_td.innerText = `${task}`;
        task_row.appendChild(int_td);
        task_row.appendChild(key_td);
        taskTableBody.appendChild(task_row);
    }
}

/**
 *
 * @param task
 * @param task_row
 */
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
    // Evemt listener for actions button: revoke task - in each task row
    actions_btn.addEventListener("click", function () {
        RESTCeleryTaskPOST(actions_btn.dataset, workerButtonsDrawToastConfirm)
    });
}

/**
 *
 * @param tabsDataset
 * @param result
 */
function workerButtonsDrawToastConfirm(tabsDataset, result) {
    // Draw toast with confirmation
    console.log("workerButtonsDrawToastConfirm");

    let dataAttrs = '';
    let toastId = '';
    let toastHeader = '';

    // Draw for single task revoke by id:
    if (tabsDataset.operation_key === 'task_revoke_by_id') {
        console.log("Draw toast for oper: 'task_revoke_by_id'");
        let async_result = result.response["async_result"];
        dataAttrs = [
            {"desc": "id", "value": async_result["task_id"], "param": "task-request", "attr": "id"},
            {"desc": "id", "value": async_result["id"], "param": "task-revoked", "attr": "id"},
            {"desc": "State", "value": async_result["state"], "param": "task-state", "attr": "id"},
            {"desc": "Status", "value": async_result["status"], "param": "task-status", "attr": "id"},
            {"desc": "Date time", "value": async_result["date_done"], "param": "task-time", "attr": "id"},
        ];
        toastId = async_result["id"];
        toastHeader = 'Revoke task by id';
    // Draw for one or multiple tasks revoked active running. Worker or not.
    } else if (tabsDataset.operation_key === 'task_revoke_active') {
        console.log("Draw toast for oper: 'task_revoke_active'");
        let revoked_tasks = result.response["revoked_tasks"];
        let revoked_count = result.response["revoked_count"];
        dataAttrs = [
            {"desc": "All", "value": revoked_count, "param": "revoked-count", "attr": "id"},
        ];
        for (let task of revoked_tasks) {
            let task_details = {"desc": "id", "value": task["id"], "param": "revoke-task-id", "attr": "class"};
            dataAttrs.push(task_details);
        }
        toastId = revoked_tasks[0]["id"];
        toastHeader = 'Revoke task active';
        // Draw for one or multiple tasks revoked reserved for run. Worker or not.
    } else if (tabsDataset.operation_key === 'task_revoke_reserved') {
        console.log("Draw toast for oper: 'task_revoke_reserved'");
        let revoked_tasks = result.response["revoked_tasks"];
        let revoked_count = result.response["revoked_count"];
        dataAttrs = [
            {"desc": "All", "value": revoked_count, "param": "revoked-count", "attr": "id"},
        ];
        for (let task of revoked_tasks) {
            let task_details = {"desc": "id", "value": task["id"], "param": "revoke-task-id", "attr": "class"};
            dataAttrs.push(task_details);
        }
        toastId = revoked_tasks[0]["id"];
        toastHeader = 'Revoke task reserved';
        // Draw for one or multiple tasks revoked active + reserved for run. Worker or not.
    } else if ((tabsDataset.operation_key === 'task_revoke_active_reserved')) {
        console.log("Draw toast for oper: 'task_revoke_active_reserved'");
        let revoked_active = result.response["revoked_active"];
        let revoked_reserved = result.response["revoked_reserved"];

        dataAttrs = [];
        dataAttrs.push({"desc": "Active", "value": revoked_active["revoked_count"], "param": "revoked-active", "attr": "id"});
        for (let task of revoked_active["revoked_tasks"]) {
            let task_details = {"desc": "id", "value": task["id"], "param": "revoke-task-id", "attr": "class"};
            dataAttrs.push(task_details);
        }
        dataAttrs.push({"desc": "Reserved", "value": revoked_reserved["revoked_count"], "param": "revoked-reserved", "attr": "id"});
        for (let task of revoked_reserved["revoked_tasks"]) {
            let task_details = {"desc": "id", "value": task["id"], "param": "revoke-task-id", "attr": "class"};
            dataAttrs.push(task_details);
        }
        toastId = "task_revoke_active_reserved";
        toastHeader = 'Revoke task active + reserved';
        // Draw for worker ping
    } else if (tabsDataset.operation_key === 'worker_ping') {
        console.log("Draw toast for oper: 'worker_ping'");
        dataAttrs = [];
        dataAttrs.push({"desc": "Ping worker", "value": JSON.stringify(result.response), "param": "worker-ping", "attr": "class"});
        toastId = 'workerPing_'+tabsDataset["workers"];
        toastHeader = 'Worker ping';
        // Draw for worker heartbeat
    } else if (tabsDataset.operation_key === 'worker_heartbeat') {
        console.log("Draw toast for oper: 'worker_heartbeat'");
        dataAttrs = [];
        dataAttrs.push({"desc": "Heartbeat worker", "value": JSON.stringify(result.response), "param": "worker-heartbeat", "attr": "class"});
        toastId = 'workerHeartbeat_'+tabsDataset["workers"];
        toastHeader = 'Worker heartbeat';
    }

    console.log(result);
    let toastBase = getToastDraftWithId(toastId, toastHeader);  // Make unique copy of toast draft
    let toastReady = fillToastBodyWithTestAttributes(toastBase, dataAttrs);  // fill toast with data
    appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:
    $('#' + toastBase.id).toast('show')
}

/**
 * TOAST:
 */


/**
 *
 * @param toastId
 * @param toastHeader
 * @returns {Node}
 */
function getToastDraftWithId(toastId = undefined, toastHeader) {
    let toastDraft = document.getElementById('toastDraft'); // Get draft toast from page foot
    let toastBase = toastDraft.children[0].cloneNode(true);  // Toast object
    toastBase.setAttribute('data-delay', 5000); // 5 sec. Wait to task mod
    if (toastId) {
        toastBase.id = toastId;
    } else {
        toastBase.id = 'NoId-UseDefault';
        console.log('WARNING: There is no unique attributes to assign as toast ID, use default!')
    }
    // Toast elements:
    // toastBase.childNodes[1];  // toast-header
    let toastHead = toastBase.childNodes[1].childNodes[3];
    toastHead.innerText = toastHeader;
    // toastBase.childNodes[3];  // toast-body
    return toastBase
}

/**
 *
 * @param toastBase
 * @param dataAttrs
 * @returns {*}
 */
function fillToastBodyWithTestAttributes(toastBase, dataAttrs) {
    let toastBody = toastBase.childNodes[3];  // Path to toast body.
    let toastDetails = document.createElement('div');
    for (let item of dataAttrs) {
        let item_div = document.createElement('div');
        let attr = item["attr"];
        let param = item["param"];
        item_div.setAttribute(`${attr}`, `${param}`);
        item_div.innerText = `${item["desc"]}: ${item["value"]}`;
        toastDetails.appendChild(item_div);
    }
    toastBody.appendChild(toastDetails);
    return toastBase
}

/**
 *
 * @param toastReady
 */
function appendToastToStack(toastReady) {
    document.getElementById('toastStack').appendChild(toastReady);
}


/**
 * REST
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
