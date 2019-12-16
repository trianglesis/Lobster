$(document).ready(function () {
    //Find table of cases tests result
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
                    if (tableRows[t_row].cells['case_id'] && tableRows[t_row].cells['fails']) {
                        // Assign values
                        let currentRow = tableRows[t_row];
                        let tdNode_fails = parseInt(tableRows[t_row].cells['fails'].textContent, 10);
                        let tdNode_error = parseInt(tableRows[t_row].cells['error'].textContent, 10);
                        let tdNode_passed = parseInt(tableRows[t_row].cells['passed'].textContent, 10);
                        let tdNode_skipped = parseInt(tableRows[t_row].cells['skipped'].textContent, 10);
                        let tdNode_className = currentRow.className;

                        let trData = {
                            // currentRow: currentRow,
                            currentRowClassName: tdNode_className,
                            tdNode_fails: tdNode_fails,
                            tdNode_error: tdNode_error,
                            tdNode_passed: tdNode_passed,
                            tdNode_skipped: tdNode_skipped,
                        };
                        // console.table(trData);

                        if (tdNode_fails > 0) {
                            currentRow.className = 'tst-notpass';
                            // currentRow.style.backgroundColor = '#E5C4CB';
                        } else if (tdNode_error >= 1 && tdNode_fails <= 0) {
                            currentRow.className = 'tst-error';
                            // currentRow.style.backgroundColor = '#F9F1D5';
                        } else if (tdNode_passed > 0 && tdNode_error < 1 && tdNode_fails < 1) {
                            currentRow.className = 'tst-pass';
                            // currentRow.style.backgroundColor = '#C6DABA';
                        } else if (tdNode_skipped > 0 && tdNode_passed < 1) {
                            currentRow.className = 'tst-skip';
                            // currentRow.style.backgroundColor = '#9998AE';
                        } else {
                            currentRow.className = 'tst-None';
                            // currentRow.style.backgroundColor = '#bfcbd4';
                        }
                        // Table with single test.py logs
                    } else if (tableRows[t_row].cells['tst_status']) {
                        // Assign values
                        let currentRow = tableRows[t_row];
                        if (tableRows[t_row].cells['tst_status'].textContent) {

                            let tdNode_tst_status = tableRows[t_row].cells['tst_status'].textContent;

                            if (tdNode_tst_status === 'ERROR') {
                                currentRow.className = 'tst-error';
                                // currentRow.style.backgroundColor = '#F9F1D5';
                            } else if (tdNode_tst_status === 'FAIL') {
                                currentRow.className = 'tst-notpass';
                                // currentRow.style.backgroundColor = '#E5C4CB';
                            } else if (tdNode_tst_status === 'ok') {
                                currentRow.className = 'tst-pass';
                                // currentRow.style.backgroundColor = '#C6DABA';
                            } else if (tdNode_tst_status === 'skip') {
                                currentRow.className = 'tst-skip';
                                // currentRow.style.backgroundColor = '#9998AE';
                            } else {
                                currentRow.className = 'tst-None';
                                // currentRow.style.backgroundColor = '#bfcbd4';
                            }
                        } else {
                            // console.log("No tst status cell found in this row or it's empty")
                        }
                    } else {
                        // console.log("Should be 1st and last TR: " + tableRows[t_row])
                    }
                } else {
                    // console.log("Table row incorrect: " + tableRows)
                }
            }
        } else {
            // console.log("Tables cannot be iterated")
        }
    }
});