$(document).ready(function () {
    console.log("Main page ready");
    getCeleryWorkersStatus();
});

function getCeleryWorkersStatus() {
    let workersList = [];
    let tasksBody = undefined;
    let workerQueues = RESTGetCeleryWorkersQueues(workersList, tasksBody, createWorkerRow);
    // console.table(workerQueues);
    createWorkerRow(workerQueues);
    repeatInspectContinuously();
}

function createWorkerRow(workerQueues) {
    let workerTable = document.getElementById('worker-table');
    // Iter list:
    for (const [workerName, workerValue] of Object.entries(workerQueues)) {
        let workerRow = document.createElement('tr');
        let workerNameCell = document.createElement('td');
        let workerTaskCountCell = document.createElement('td');
        let workerTaskCountButton = document.createElement('a');

        workerRow.setAttribute('id', workerName);
        workerNameCell.setAttribute('class', 'bg-light text-dark');
        workerNameCell.style.textAlign = `left`;
        workerTaskCountCell.setAttribute('class', 'bg-light text-center text-dark');
        workerTaskCountButton.setAttribute('class', 'btn btn-sm-er btn-outline-dark');
        workerTaskCountButton.href = `/octo_admin/celery_inspect/?workers=${workerName.split('@')[0]}`;
        workerTaskCountButton.textContent = `${workerName}`;
        workerTaskCountCell.innerText = `${workerValue}`;

        workerNameCell.appendChild(workerTaskCountButton);
        workerRow.appendChild(workerNameCell);
        workerRow.appendChild(workerTaskCountCell);
        workerTable.appendChild(workerRow);
    }

}

/**
 * Inspect workers with short version.
 * @param workerList
 * @param tasksBody
 * @param createWorkerRow
 * @returns {Array}
 * @constructor
 */
function RESTGetCeleryWorkersQueues(workerList, tasksBody, createWorkerRow) {
    let data = {};
    if (tasksBody) {
        data.task_body = '1';
    }
    if (workerList) {
        data.workers_list = workerList;
    }

    $.ajax({
        "type": "GET",
        "dataType": "json",
        contentType: "application/json; charset=utf-8",
        "url": "/inspect_rabbitmq_queues/",
        data: data,
        "beforeSend": function (xhr, settings) {
            $.ajaxSettings.beforeSend(xhr, settings)
        },
        "success": function (result) {
            // console.log(`GET result: ${result}`);
            if (result) {
                // console.table(result);
                createWorkerRow(result)
            } else {
                console.error("Task GET failed, no task found or no status");
            }
        },
        "error": function () {
            console.error("GET TASK ERROR, something goes wrong...");
        },
    });
    return [];
}

function repeatInspectContinuously() {

}
