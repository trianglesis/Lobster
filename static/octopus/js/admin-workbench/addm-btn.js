$(document).ready(function () {
    $('#addmButtonsModal').on('hidden.bs.modal', function (event) {
        $('#addmButtonsModal').modal('hide');
    });
});

$(document).ready(function () {

    $('#addmButtonsModal').on('show.bs.modal', function (event) {
        let modal = document.getElementById("addmButtonsModal");
        let tableRow = getTableRowFromEvent(event);
        let addmButtons = document.getElementsByClassName('addm-btn');

        let modalDetails = modal.childNodes[1].childNodes[1].childNodes[3].firstElementChild;
        let par = document.createElement('p');
        par.innerText = `${tableRow.cells['addm_group'].textContent} | ${tableRow.cells['branch_lock'].textContent} | ${tableRow.cells['addm_name'].textContent} | ${tableRow.cells['addm_v_int'].textContent} | ${tableRow.cells['addm_host'].textContent} | ${tableRow.cells['addm_ip'].textContent}`;
        modalDetails.appendChild(par);

        console.table(tableRow.cells['addm_host'].textContent);
        for (let btn of addmButtons) {
            let old_href = btn.href;
            let new_href = old_href.replace('__addm.addm_host__', tableRow.cells['addm_host'].textContent);
            btn.href = new_href;
            console.log(new_href);
        }

    });


});