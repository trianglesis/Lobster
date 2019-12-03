function changeFunc() {
    let sortedKeys = [];
    let selectBox = document.getElementById("addmCMDSelect");
    let allOptions = selectBox.options;
    for (let selected of allOptions) {
        if (selected.selected) {
            if (sortedKeys.includes(selected.value)){
                console.log('Already selected')
            } else {
                sortedKeys.push(selected.value);
            }
        }
    }
    console.log(sortedKeys);
}