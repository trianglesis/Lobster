/**
 *
 */

let tabsDataset = {
    'operation_key': 'tasks_get_active_reserved',
    'workers': undefined,
};


// let TEMP_Rest_response = {"active":{"w_routines@tentacle":[],"w_parsing@tentacle":[],"charlie@tentacle":[{"id":"28e860eb-bfef-4941-965c-7212161ea6e8","name":"octo.tasks.fake_task","args":"['fire_t', 2400]","kwargs":"{'t_args': ['tag=t_test_exec_threads;type=user_routine;branch=tkn_ship;addm_group=charlie;user_name=octopus_super;refresh=False;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/10genMongoDB/tests/test.py'], 't_kwargs': {'addm_items': [{...}, {...}, {...}], 'test_item': {'id': 1009, 'test_type': 'tku_patterns', 'tkn_branch': 'tkn_ship', 'pattern_library': 'CORE', 'pattern_folder_name': '10genMongoDB', 'pattern_folder_path': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/10genMongoDB', 'pattern_library_path': '/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE', 'test_case_dir': '', 'change': '789132', 'change_desc': 'CUSTOMER|DEFECT|DRDC1-14354|Use correct key when none of port, instance or db path are discovered|@1009586\n\nMerging\n\n//addm/tkn_main/tku_patterns/CORE/10genMongoDB/...\n\nto //addm/tkn_main/tku_patterns/CORE/10genMongoDB/...\n', 'change_user': 'yzeinalo', 'change_review': '#1009586', 'change_ticket': 'DRDC1-14354', 'change_time': datetime.dateti..., ...}}}","type":"octo.tasks.fake_task","hostname":"charlie@tentacle","time_start":1576147275.5120533,"acknowledged":true,"delivery_info":{"exchange":"","routing_key":"charlie@tentacle.dq2","priority":null,"redelivered":true},"worker_pid":2688935593832}],"golf@tentacle":[],"alpha@tentacle":[{"id":"92ddad2b-6c45-4eb9-9e73-364bec09c8c0","name":"octo.tasks.fake_task","args":"['fire_t', 2400]","kwargs":"{'t_args': ['tag=t_test_exec_threads;type=user_routine;branch=tkn_main;addm_group=alpha;user_name=octopus_super;refresh=False;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/Common/tests/test.py'], 't_kwargs': {'addm_items': [{...}, {...}, {...}, {...}], 'test_item': {'id': 8, 'test_type': 'tku_patterns', 'tkn_branch': 'tkn_main', 'pattern_library': 'STORAGE', 'pattern_folder_name': 'Common', 'pattern_folder_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/Common', 'pattern_library_path': '/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE', 'test_case_dir': '', 'change': '766638', 'change_desc': '@754252 - New | CUSTOMER | DRDC1-9158 | WELLSFARGO/STORAGE: EMC Isilon discovery via REST API\n', 'change_user': 'pthiyaga', 'change_review': '#754252', 'change_ticket': 'DRDC1-9158', 'change_time': datetime.datetime(2019, 4, 16, 16, 45, 35, tzinfo=<UTC>), 'test_case_depot_path': '//addm/tkn_main/tku_patterns/STORAGE/Common', 'test_py_path': '/home...', ...}}}","type":"octo.tasks.fake_task","hostname":"alpha@tentacle","time_start":1576147275.520032,"acknowledged":true,"delivery_info":{"exchange":"","routing_key":"alpha@tentacle.dq2","priority":null,"redelivered":true},"worker_pid":2228060158256}]},"reserved":{"w_parsing@tentacle":[],"alpha@tentacle":[{"id":"e9e78543-9893-4f9f-a9a3-f97c4cb80278","name":"octo.tasks.fake_task","args":"['fire_t', 10]","kwargs":"{'t_args': ['tag=t_user_mail;mode=finish;addm_group=alpha;user_name=octopus_super;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_main/tku_patterns/STORAGE/Common/tests/test.py'], 't_kwargs': {'mail_opts': {'mode': 'finish', 'view_obj': {...}, 'test_item': {...}, 'addm_set': <QuerySet [{'id': 6, 'addm_host': 'vl-aus-tkudev-38', 'addm_name': 'custard_cream', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.144.118', 'addm_v_code': 'ADDM_11_2', 'addm_v_int': '11.2', 'addm_full_version': '11.2.0.6', 'addm_branch': 'r11_2_0_x', 'addm_owner': 'Alex D', 'addm_group': 'alpha', 'disables': None, 'branch_lock': 'tkn_main', 'description': None, 'vm_cluster': 'tku_cluster', 'vm_id': 'vim.VirtualMachine:vm-69'}, {'id': 7, 'addm_host': 'vl-aus-tkudev-39', 'addm_name': 'bobblehat', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.144.119', 'addm_v_code': 'ADDM_11_1',...}}}","type":"octo.tasks.fake_task","hostname":"alpha@tentacle","time_start":null,"acknowledged":false,"delivery_info":{"exchange":"","routing_key":"alpha@tentacle.dq2","priority":null,"redelivered":true},"worker_pid":null}],"golf@tentacle":[],"charlie@tentacle":[{"id":"43402dbf-98da-4cc8-8e44-e5c19c500379","name":"octo.tasks.fake_task","args":"['fire_t', 10]","kwargs":"{'t_args': ['tag=t_user_mail;mode=finish;addm_group=charlie;user_name=octopus_super;test_py_path=/home/user/TH_Octopus/perforce/addm/tkn_ship/tku_patterns/CORE/10genMongoDB/tests/test.py'], 't_kwargs': {'mail_opts': {'mode': 'finish', 'view_obj': {...}, 'test_item': {...}, 'addm_set': <QuerySet [{'id': 12, 'addm_host': 'vl-aus-rem-qa6n', 'addm_name': 'custard_cream', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.148.106', 'addm_v_code': 'ADDM_11_2', 'addm_v_int': '11.2', 'addm_full_version': '11.2.0.6', 'addm_branch': 'r11_2_0_x', 'addm_owner': 'Alex D', 'addm_group': 'charlie', 'disables': None, 'branch_lock': 'tkn_ship', 'description': None, 'vm_cluster': 'pune', 'vm_id': None}, {'id': 13, 'addm_host': 'vl-aus-rem-qa6p', 'addm_name': 'bobblehat', 'tideway_user': 'tideway', 'tideway_pdw': 'S0m3w@y', 'root_user': 'root', 'root_pwd': 'tidewayroot', 'addm_ip': '172.25.148.107', 'addm_v_code': 'ADDM_11_1', 'addm_v_int': '11.1',...}}}","type":"octo.tasks.fake_task","hostname":"charlie@tentacle","time_start":null,"acknowledged":false,"delivery_info":{"exchange":"","routing_key":"charlie@tentacle.dq2","priority":null,"redelivered":true},"worker_pid":null}],"w_routines@tentacle":[]}};
// console.log("TEMP_Rest_response");
// console.log(TEMP_Rest_response);

/**
 * Initial run of task inspections with default args: active+reserved for all workers.
 */
$(document).ready(function () {
    console.log("Page loaded, now inspect workers!");
    console.log("Django template global var: single_worker - " + single_worker);

    // Inspect all workers or one selected:
    if (single_worker === 'all-workers') {
        console.log("Inspect all available workers. Not specify");
    } else {
        console.log("Inspect one worker: " + single_worker);
        tabsDataset.workers = single_worker;
    }
    getWorkersTaskStatuses(tabsDataset);
});

/**
 * Initial task inspect for active and reserved on page open.
 * If worker is globally assigned - show only worker related tasks.
 */
function getWorkersTaskStatuses() {
    // Inspect all workers (or one selected) for active+reserved tasks:
    RESTCeleryTaskPOST(tabsDataset, modifyCeleryTabContent);
    // Assign listeners for each tab:
    eventListenerCeleryTabs(fillCeleryTabs);
    eventListenerCeleryMainButtons();
}

/**
 * Task inspect when tab pushed, of worker selected - show only worker related tasks
 * @param tabsDataset
 */
function fillCeleryTabs(tabsDataset) {
    if (tabsDataset.workers === 'all-workers') {
        console.log("All workers!");
        delete tabsDataset['workers'];
        console.table(tabsDataset);
    }
    RESTCeleryTaskPOST(tabsDataset, modifyCeleryTabContent);
}

function modifyCeleryTabContent(tabsDataset, RESTResult) {
    // RESTResult.response = TEMP_Rest_response;

    let workerCard = document.getElementById("worker-card");
    let tabActiveReserved = document.getElementById("active-reserved");
    // let tabActive = document.getElementById("active");
    // let tabReserved = document.getElementById("reserved");
    // let tabScheduled = document.getElementById("scheduled");
    let tabRegistered = document.getElementById("registered");

    if (tabsDataset.operation_key === 'tasks_get_active_reserved') {
        prepareTabContent("active-reserved");
        fillTabTaskTableActRes(tabActiveReserved, workerCard, RESTResult)
    }

    // if (tabsDataset.operation_key === 'tasks_get_active') {
    //     prepareTabContent("active");
    //     fillTabTaskTable_(tab_active, worker_card, RESTResult)
    // }
    //
    // if (tabsDataset.operation_key === 'tasks_get_reserved') {
    //     prepareTabContent("reserved");
    //     fillTabTaskTable_(tab_reserved, worker_card, RESTResult)
    // }
    // if (tabsDataset.operation_key === 'tasks_get_scheduled') {
    //     prepareTabContent("scheduled");
    //     for (const [key, value] of Object.entries(RESTResult.response)) {
    //         let item_p = document.createElement('p');
    //         item_p.innerText = `${key}: ${value}`;
    //         fillScheduledRegisteredTasks(tabScheduled, workerCard, RESTResult);
    //     }
    // }

    if (tabsDataset.operation_key === 'tasks_get_registered') {
        prepareTabContent("registered");
        for (const [key, value] of Object.entries(RESTResult.response)) {
            let item_p = document.createElement('p');
            item_p.innerText = `${key}: ${value}`;
            fillScheduledRegisteredTasks(tabRegistered, workerCard, RESTResult);
        }
    }
}
