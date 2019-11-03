/**
 *
 */

$(document).ready(function () {
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

function fillTabTaskTable(tabNode, worker_card, RESTResult) {
    let argsShow = ['id', 'name', 'args', 'time_start', 'type'];
    for (const [w_key, w_value] of Object.entries(RESTResult.response)) {

        let workerCardBase = worker_card.children[0].cloneNode(true);
        let cardHeader = workerCardBase.childNodes[1];  // Header
        let cardBody = workerCardBase.childNodes[3];  // Body

        cardHeader.innerText = `${w_key}`;  // worker name

        if (w_value && w_value.length > 0) {
            let taskTableBody = cardBody.firstElementChild.tBodies[0];  // Task table
            for (let task of w_value) {
                let task_row  = document.createElement('tr');
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
        fillTabTaskTable(tab_active_reserved, worker_card, RESTResult)
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