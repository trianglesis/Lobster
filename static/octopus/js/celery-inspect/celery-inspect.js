/**
 *
 */

let tabsDataset = {
    'operation_key': 'tasks_get_active',
    'workers': undefined,
};
let pingWorkers = {
    'operation_key': 'worker_ping',
};
let actualWorkers = [];


$(document).ready(function () {
    console.log("Page loaded, now inspect workers!");
    console.log(single_worker);

    if (single_worker === 'all-workers') {
        console.log("Inspect all available workers. Not specify");
    } else {
        console.log("Inspect one worker: " + single_worker);
        tabsDataset.workers = single_worker;
    }
    // TODO: Initially - get all available workers by pinging all:
    RESTCeleryTaskPOST(pingWorkers, assignActualWorkers);

    // Inspect all possible workers for active tasks
    RESTCeleryTaskPOST(tabsDataset, modifyCeleryTabContent);
    eventListenerCeleryTabs(fillCeleryTabs)
});

function fillCeleryTabs(tabsDataset) {
    if (tabsDataset.workers === 'all-workers') {
        console.log("All workers!");
        delete tabsDataset['workers'];
        console.table(tabsDataset);
    }
    RESTCeleryTaskPOST(tabsDataset, modifyCeleryTabContent);
}

function modifyCeleryTabContent(tabsDataset, RESTResult) {
    // console.table(RESTResult);
    let worker_card = document.getElementById("worker-card");
    let tab_active = document.getElementById("active");
    let tab_reserved = document.getElementById("reserved");
    let tab_active_reserved = document.getElementById("active-reserved");
    let tab_scheduled = document.getElementById("scheduled");
    let tab_registered = document.getElementById("registered");

    if (tabsDataset.operation_key === 'tasks_get_active') {
        console.table(RESTResult.response);
        tab_active.querySelectorAll('*').forEach(n => n.remove());
        fillTabTaskTable(tab_active, worker_card, RESTResult)
    }
    if (tabsDataset.operation_key === 'tasks_get_reserved') {
        console.table(RESTResult.response);
        tab_reserved.querySelectorAll('*').forEach(n => n.remove());
        fillTabTaskTable(tab_reserved, worker_card, RESTResult)
    }
    if (tabsDataset.operation_key === 'tasks_get_active_reserved') {
        console.table(RESTResult.response);
        tab_active_reserved.querySelectorAll('*').forEach(n => n.remove());
        fillTabTaskTableActRes(tab_active_reserved, worker_card, RESTResult)
    }
    if (tabsDataset.operation_key === 'tasks_get_scheduled') {
        console.table(RESTResult.response);
        tab_scheduled.querySelectorAll('*').forEach(n => n.remove());

        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            tab_scheduled.appendChild(item_p)
        }
    }
    if (tabsDataset.operation_key === 'tasks_get_registered') {
        console.table(RESTResult.response);
        tab_registered.querySelectorAll('*').forEach(n => n.remove());

        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            tab_registered.appendChild(item_p)
        }
    }
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

function fillTabTaskTableActRes(tabNode, worker_card, RESTResult) {
    let argsShow = ['id', 'name', 'args', 'time_start', 'type'];
    // let tasks = unpackActiveReserved(RESTResult.response);

    for (const [ins_key, ins_value] of Object.entries(RESTResult.response)) {
        if (ins_value) {
            console.log(`stat: ${ins_key}`);
            for (const [w_key, w_value] of Object.entries(ins_value)) {

                if (w_value.length > 0) {
                    let workerCardBase = worker_card.children[0].cloneNode(true);
                    let cardHeader = workerCardBase.childNodes[1];  // Header
                    let cardBody = workerCardBase.childNodes[3];  // Body

                    cardHeader.childNodes[0].innerText = `${w_key}`;  // worker name

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
                        }
                    }
                    tabNode.appendChild(workerCardBase)
                }
            }
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
}

function assignActualWorkers(dataset, RESTWorkersPingResponse) {
    if (RESTWorkersPingResponse) {
        actualWorkers = RESTWorkersPingResponse;
        console.log(actualWorkers.response);
    } else {
        console.log("NO actual workers found by ping!")
    }

}

function taskOperationsButtonsToast(btnDataset) {
    console.log(btnDataset);
    // Make REST request with operation key and opts:
    RESTCeleryTaskPOST(btnDataset, drawToastConfirm);
}

function drawToastConfirm(tabsDataset, result) {
    // Draw toast with confirmation
    console.log(tabsDataset);
    console.log(result);
}