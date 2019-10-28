$(document).ready(function () {
    let failMessagesCells = document.getElementsByClassName('fail_message');
    let Actual = /(?:Actual|Actual - Expected:)(.*)/g;
    let Expected = /(?:Expected|Expected - Actual:)(.*)/g;
    let AssertionError = /AssertionError:(.*)/gms;
    let AssertionErrorFound = /AssertionError: Found (.*)/g;
    let AssertionErrorServererror = /AssertionError: Server error (.*)/g;
    let ExecutionFailureCORBA = /ExecutionFailure: ModelCORBA(.*)/g;
    let IOError = /IOError(.*)/g;
    let TypeError = /TypeError(.*)/g;
    let KeyError = /KeyError(.*)/g;
    let ParseException = /ParseException:(.*)/g;
    let AttributeError = /AttributeError:(.*)/g;

    for (let cell of failMessagesCells) {
        // console.log(cell.innerText);
        let foundActual = cell.innerText.match(Actual);
        let foundExpected = cell.innerText.match(Expected);
        if (foundActual && foundExpected) {
            console.log(`foundActual ${foundActual}`);
            console.log(`foundExpected ${foundExpected}`);
            cell.innerText = `${foundActual}\n${foundExpected}`
        } else if (cell.innerText.match(AssertionError)) {
            cell.innerText = `${cell.innerText.match(AssertionError)}`
        } else if (cell.innerText.match(AssertionErrorFound)) {
            cell.innerText = `${cell.innerText.match(AssertionErrorFound)}`
        } else if (cell.innerText.match(AssertionErrorServererror)) {
            cell.innerText = `${cell.innerText.match(AssertionErrorServererror)}`
        } else if (cell.innerText.match(ExecutionFailureCORBA)) {
            cell.innerText = `${cell.innerText.match(ExecutionFailureCORBA)}`
        } else if (cell.innerText.match(IOError)) {
            cell.innerText = `${cell.innerText.match(IOError)}`
        } else if (cell.innerText.match(TypeError)) {
            cell.innerText = `${cell.innerText.match(TypeError)}`
        } else if (cell.innerText.match(KeyError)) {
            cell.innerText = `${cell.innerText.match(KeyError)}`
        } else if (cell.innerText.match(ParseException)) {
            cell.innerText = `${cell.innerText.match(ParseException)}`
        } else if (cell.innerText.match(AttributeError)) {
            cell.innerText = `${cell.innerText.match(AttributeError)}`
        } else {

        }


    }



});