$(document).ready(function () {
    $('#addmCMDRun').on('hidden.bs.modal', function (event) {
        $('#addmCMDRun').modal('hide');
    });
});

function addmCMDkeysSelected() {
    let selectedCMDs = [];
    let selectBox = document.getElementById("addmCMDSelect");
    let allOptions = selectBox.options;
    for (let selected of allOptions) {
        if (selected.selected) {
            if (selectedCMDs.includes(selected.value)) {
                console.log('Already selected')
            } else {
                selectedCMDs.push(selected.value);
            }
        }
    }
    console.log(selectedCMDs);
    return selectedCMDs;
}

function addmGroupsSelected() {
    let checkedADDMs = [];
    let checkBoxes = document.getElementsByClassName("form-check-input");

    for (let checkbox of checkBoxes) {
        if (checkbox.checked) {
            if (checkedADDMs.includes(checkbox.value)) {
                console.log('Already selected')
            } else {
                checkedADDMs.push(checkbox.value);
            }
        }
    }
    console.log(checkedADDMs);
    return checkedADDMs;
}

$(document).ready(function () {
    // let modal = document.getElementById("addmCMDRun");
    let runAddmCMD = document.getElementById("runAddmCMD");

    let checkedADDMs = '';
    let selectedCMDs = '';

    runAddmCMD.addEventListener("click", function () {
        checkedADDMs = addmGroupsSelected();
        selectedCMDs = addmCMDkeysSelected();
        runAddmCMD.dataset.operation_key = 'addm_cmd_run';
        runAddmCMD.dataset.addm_group = checkedADDMs.join(',');
        runAddmCMD.dataset.command_key = selectedCMDs.join(',');

        let toastBase = getToastDraft(runAddmCMD.dataset);
        let toastReady = fillToastBodyWithTaskDetails(runAddmCMD.dataset, toastBase);
        appendToastToStack(toastReady);  //  Appending composed toast to toast stack on page:

        RESTAdminOperationsPOST(runAddmCMD.dataset, toastReady);
        showToastTask(toastReady.id); // Make toast visible
        hideModal('addmCMDRun'); // Make toast visible
    });

});