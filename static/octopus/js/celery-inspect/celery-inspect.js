/**
 *
 */

$(document).ready(function () {
    eventListenerCeleryTabs(fillCeleryTabs)
});

function fillCeleryTabs(tabsDataset) {
    if (tabsDataset.workers === 'all-workers') {
        console.log("All workers!");
        delete tabsDataset['workers'];
        console.table(tabsDataset);
    }

    RESTCeleryTaskPOST(tabsDataset, modifyCeleryTabContent);
}

function modifyCeleryTabContent(RESTResult) {
    console.table(RESTResult);
}