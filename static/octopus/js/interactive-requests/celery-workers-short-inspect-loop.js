$(document).ready(function () {
    console.log("Main page ready");
    getCeleryWorkersStatus();
});

function getCeleryWorkersStatus() {
    let workersList = [];
    let tasksBody = undefined;
    let workerQueues = new RESTGetCeleryWorkersQueues(workersList, tasksBody, createWorkerRow);
    // console.table(workerQueues);
    createWorkerRow(workerQueues);
    repeatInspectContinuously();
}

function createWorkerRow(workerQueues) {
    let workerTable = document.getElementById('worker-table');
    // console.table(workerTable);

    // Iter list:
    for (let workerItem of workerQueues) {
        for (const [workerName, workerValue] of Object.entries(workerItem)) {
            let workerRow = document.createElement('tr');
            let workerNameCell = document.createElement('td');
            let workerTaskCountCell = document.createElement('td');
            let workerTaskCountButton = document.createElement('a');


            workerRow.setAttribute('id', workerName);
            workerNameCell.setAttribute('class', 'bg-light text-dark');
            workerNameCell.style.textAlign = `left`;
            workerTaskCountCell.setAttribute('class', 'bg-light text-center text-dark');
            workerTaskCountButton.setAttribute('class', 'btn btn-sm-er btn-outline-dark');
            workerTaskCountButton.href = `/octo_admin/workers_status_single/?worker_name=${workerName}`;
            workerTaskCountButton.textContent = `${workerName}`;
            workerTaskCountCell.innerText = `${workerValue['all_tasks_len']}`;


            workerNameCell.appendChild(workerTaskCountButton);
            workerRow.appendChild(workerNameCell);
            workerRow.appendChild(workerTaskCountCell);
            workerTable.appendChild(workerRow);
        }
    }

}

function repeatInspectContinuously() {

}
