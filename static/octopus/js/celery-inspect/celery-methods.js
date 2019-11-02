/**
 *
 **/



function eventListenerCeleryTabs(funcToRun) {
    let nav_active_tab = document.getElementById("nav-active-tab");
    let nav_reserved_tab = document.getElementById("nav-reserved-tab");
    let nav_active_reserved_tab = document.getElementById("nav-active-reserved-tab");
    let nav_scheduled_tab = document.getElementById("nav-scheduled-tab");
    let nav_registered_tab = document.getElementById("nav-registered-tab");

    nav_active_tab.addEventListener("click", function () {
        funcToRun(nav_active_tab.dataset)
    });
    nav_reserved_tab.addEventListener("click", function () {
        funcToRun(nav_reserved_tab.dataset)
    });
    nav_active_reserved_tab.addEventListener("click", function () {
        funcToRun(nav_active_reserved_tab.dataset)
    });
    nav_scheduled_tab.addEventListener("click", function () {
        funcToRun(nav_scheduled_tab.dataset)
    });
    nav_registered_tab.addEventListener("click", function () {
        funcToRun(nav_registered_tab.dataset)
    });
}




/**
 * @return {string}
 */
function RESTCeleryTaskPOST(tabsDataset, nextFunc) {
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/x-www-form-urlencoded",
        url: '/octo_admin/task_operation/',
        data: tabsDataset,
        "beforeSend": function (xhr, settings) {$.ajaxSettings.beforeSend(xhr, settings)},
        "success": function (result) {
            console.log(`POST result: ${result}`);
            if (result) {
                nextFunc(result)
            } else {
                console.log("Task POST send, but haven't been added. No task_id in result!")
            }
        },
        "error": function () {
            console.log("POST TASK ERROR, something goes wrong...")
        },
    });
    return 'testButtonDataset';
}