$(document).ready(function () {
    // Find table of cases tests result
    let tableNodes = document.getElementsByTagName('table');
    // console.table(tableNodes);

    // Iter over all tables found on the page!
    for (let table in tableNodes) {
        // If table is in tables:
        if (tableNodes.hasOwnProperty(table)) {
            // Assign single table:
            let tableRows = tableNodes[table].rows;
            // console.table(tableRows);

            // For index in table rows
            for (let t_row in tableRows) {
                //If table row is actual
                if (tableRows.hasOwnProperty(t_row)) {
                    // console.log(tableRows[t_row]);
                    //If table row has case in it (excluding th rows)
                    if (tableRows[t_row].cells['package_type']) {
                        // Assign values
                        let currentRow = tableRows[t_row];
                        // console.table(currentRow);
                        let tdNode_addm_name = tableRows[t_row].cells['addm_name'].textContent;
                        let tdNode_test_mode = tableRows[t_row].cells['test_mode'].textContent;
                        let tdNode_package_type = tableRows[t_row].cells['package_type'].textContent;
                        let tdNode_mode_key = tableRows[t_row].cells['mode_key'].textContent;
                        // let debug_str = `${tdNode_addm_name} ${tdNode_test_mode} ${tdNode_package_type}`;

                        let tdNode_upload_test_status = tableRows[t_row].cells['upload_test_status'].textContent;
                        let tdNode_all_errors = parseInt(tableRows[t_row].cells['all_errors'].textContent, 10);
                        let tdNode_time_spent_test = parseInt(tableRows[t_row].cells['time_spent_test'].textContent, 10);

                        let tdNode_upload_errors = JSON.parse(tableRows[t_row].cells['upload_errors'].textContent);


                        // Mark red if upload test status is fail, or errors > 0, or test time run less then few min:
                        if (tdNode_all_errors > 0) {
                            // console.log(`Not Pass have ERRORS: ${tdNode_all_errors} ${debug_str}`);
                            currentRow.className = 'tst-notpass';

                        } else if (tdNode_time_spent_test < 300) {
                            // console.log(`Not Pass too short time of install : ${tdNode_time_spent_test} ${debug_str}`);
                            if (tdNode_mode_key.includes('TKU-Product-Content') || tdNode_mode_key.includes('tideway-devices')) {
                                currentRow.className = 'tst-None';
                            } else {
                                currentRow.className = 'tst-notpass';
                            }

                            // Stupidly compare '[]' array, if more that 2 items - it could have errors from upload test
                        } else if (tdNode_upload_errors.length > 2) {
                            // console.log(`Not pass, upload ERRORs list is not empty : '${tdNode_upload_errors}' ${debug_str}`);
                            currentRow.className = 'tst-notpass';

                        } else if (tdNode_upload_test_status === 'passed'
                            && tdNode_all_errors === 0
                            && tdNode_time_spent_test > 300
                            && tdNode_upload_errors.length === 2
                        ) {
                            // console.log(`Passed status 'passed' error list is empty, upload time is > 5min, no upload errors : ${tdNode_upload_test_status} ${debug_str}`);
                            currentRow.className = 'tst-pass';

                        } else {
                            // console.log(`Else:
                            // upload_test_status: ${tdNode_upload_test_status}
                            // all_errors: ${tdNode_all_errors}
                            // time_spent_test: ${tdNode_time_spent_test}
                            // upload_errors: ${tdNode_upload_errors}
                            //  - ${debug_str}`);
                            currentRow.className = 'tst-None';
                        }
                    } else {
                        // console.log("Upload table row has no required cell value.")
                    }
                } else {
                    // console.log("Upload table has no row property!")
                }
            }
        }
        // else console.log("Upload table wrong property.")
    }
});