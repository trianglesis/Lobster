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
    console.table(RESTResult);

    let tab_active = document.getElementById("active");
    let tab_reserved = document.getElementById("reserved");
    let tab_active_reserved = document.getElementById("active-reserved");
    let tab_scheduled = document.getElementById("scheduled");
    let tab_registered = document.getElementById("registered");

    if (tabsDataset.operation_key === 'tasks_get_active') {
        console.table(RESTResult.response);

        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            tab_active.appendChild(item_p)
        }
    }
    if (tabsDataset.operation_key === 'tasks_get_reserved') {
        console.table(RESTResult.response);

        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            tab_reserved.appendChild(item_p)
        }
    }
    if (tabsDataset.operation_key === 'tasks_get_active_reserved') {
        console.table(RESTResult.response);

        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            tab_active_reserved.appendChild(item_p)
        }
    }
    if (tabsDataset.operation_key === 'tasks_get_scheduled') {
        console.table(RESTResult.response);

        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            tab_scheduled.appendChild(item_p)
        }
    }
    if (tabsDataset.operation_key === 'tasks_get_registered') {
        console.table(RESTResult.response);

        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            tab_registered.appendChild(item_p)
        }
    }
}