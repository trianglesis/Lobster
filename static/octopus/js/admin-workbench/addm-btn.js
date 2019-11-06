$(document).ready(function () {
    $('#addmButtonsModal').on('hidden.bs.modal', function (event) {
        $('#addmButtonsModal').modal('hide');
    });
});

$(document).ready(function () {
    $('#addmButtonsModal').on('show.bs.modal', function (event) {
        // let modal = document.getElementById("addmButtonsModal");
        let addmDetailsStr = document.getElementById("addm_details_str");
        let addmButtons = document.getElementsByClassName('addm-btn');
        let tableRow = getTableRowFromEvent(event);
        let addmHostRe = /(http:\/\/)(\S+)(\.bmc\.com)/;
        addmDetailsStr.innerText = `${tableRow.cells['addm_group'].textContent} | \
        ${tableRow.cells['branch_lock'].textContent} | ${tableRow.cells['addm_name'].textContent} | \ 
        ${tableRow.cells['addm_v_int'].textContent} | ${tableRow.cells['addm_host'].textContent} | \
        ${tableRow.cells['addm_ip'].textContent}`;
        for (let btn of addmButtons) {
            let old_href = btn.href;
            let new_href = old_href.replace(addmHostRe, `$1${tableRow.cells['addm_host'].textContent}$3`);
            btn.href = new_href;
            console.log(new_href);
        }
    });
});