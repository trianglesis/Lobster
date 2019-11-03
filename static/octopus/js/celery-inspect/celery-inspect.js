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

function modifyCeleryTabContent(tabsDataset, RESTResult) {
    // console.table(RESTResult);
    let worker_card = document.getElementById("worker-card");

    // console.table(workerCardBase);

    let tab_active = document.getElementById("active");
    let tab_reserved = document.getElementById("reserved");
    let tab_active_reserved = document.getElementById("active-reserved");
    let tab_scheduled = document.getElementById("scheduled");
    let tab_registered = document.getElementById("registered");

    if (tabsDataset.operation_key === 'tasks_get_active') {
        console.table(RESTResult.response);
        tab_active.querySelectorAll('*').forEach(n => n.remove());
        for (const [w_key, w_value] of Object.entries(RESTResult.response)) {
            let workerCardBase = worker_card.children[0].cloneNode(true);
            let cardHeader = workerCardBase.childNodes[1];  // Header
            let cardBody = workerCardBase.childNodes[3];  // Body
            let taskTableRows = cardBody.firstElementChild.tBodies[0].rows[0];  // Task table
            cardHeader.innerText = `${w_key}`;
            if (w_value && w_value.length > 0) {
                for (let task of w_value) {
                    for (const [key, val] of Object.entries(task)) {
                        let task_row  = document.createElement('tr');
                        let task_attr = document.createElement('td');
                        let task_val = document.createElement('td');

                        if (key === 'delivery_info') {
                            task_val.innerText = `${JSON.stringify(val)}`;
                        } else if (key === 'kwargs') {
                            task_val.innerText = `hidden`;
                        } else {
                            task_val.innerText = `${val}`;
                        }

                        task_attr.innerText = `${key}`;
                        task_row.appendChild(task_attr);
                        task_row.appendChild(task_val);
                        taskTableRows.appendChild(task_row);
                    }
                }
            }
            tab_active.appendChild(workerCardBase)
        }
    }
    if (tabsDataset.operation_key === 'tasks_get_reserved') {
        console.table(RESTResult.response);
        tab_reserved.querySelectorAll('*').forEach(n => n.remove());

        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            tab_reserved.appendChild(item_p)
        }
    }
    if (tabsDataset.operation_key === 'tasks_get_active_reserved') {
        console.table(RESTResult.response);
        tab_active_reserved.querySelectorAll('*').forEach(n => n.remove());

        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            tab_active_reserved.appendChild(item_p)
        }
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