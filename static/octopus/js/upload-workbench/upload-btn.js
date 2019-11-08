$(document).ready(function () {
    $('#releaseUpload').on('hidden.bs.modal', function (event) {
        $('#releaseUpload').modal('hide');
    });
});
$(document).ready(function () {
    $('#dailyUpload').on('hidden.bs.modal', function (event) {
        $('#dailyUpload').modal('hide');
    });
});
$(document).ready(function () {
    $('#wgetRefresh').on('hidden.bs.modal', function (event) {
        $('#wgetRefresh').modal('hide');
    });
});


$(document).ready(function () {
    $('#releaseUpload').on('show.bs.modal', function (event) {
        // let modal = document.getElementById("addmButtonsModal");
        let gaFreshInstall = document.getElementById('ga-fresh-install');
        let gaUpgradeInstall = document.getElementById('ga-upgrade-install');
        let releasedTknFreshInstall = document.getElementById('released-tkn-fresh-install');

        gaFreshInstall.dataset.operation_key = 'tku_install_test';
        gaUpgradeInstall.dataset.operation_key = 'tku_install_test';
        releasedTknFreshInstall.dataset.operation_key = 'tku_install_test';

        gaFreshInstall.modalId = 'releaseUpload';
        gaUpgradeInstall.modalId = 'releaseUpload';
        releasedTknFreshInstall.modalId = 'releaseUpload';

        gaFreshInstall.addEventListener('click', buttonActivationUpload);
        gaUpgradeInstall.addEventListener('click', buttonActivationUpload);
        releasedTknFreshInstall.addEventListener('click', buttonActivationUpload);

    });
});

$(document).ready(function () {
    $('#dailyUpload').on('show.bs.modal', function (event) {
        // let modal = document.getElementById("addmButtonsModal");
        let tknMainContinuousInstall = document.getElementById('tkn_main_continuous_install');
        let tknShipContinuousInstall = document.getElementById('tkn_ship_continuous_install');

        tknMainContinuousInstall.dataset.operation_key = 'tku_install_test';
        tknShipContinuousInstall.dataset.operation_key = 'tku_install_test';

        tknMainContinuousInstall.modalId = 'dailyUpload';
        tknShipContinuousInstall.modalId = 'dailyUpload';

        tknMainContinuousInstall.addEventListener('click', buttonActivationUpload);
        tknShipContinuousInstall.addEventListener('click', buttonActivationUpload);
    });
});

$(document).ready(function () {
    $('#wgetRefresh').on('show.bs.modal', function (event) {
        // let modal = document.getElementById("addmButtonsModal");
        let wgetAll = document.getElementById('wget_all');
        let wgetReleasedTkn = document.getElementById('wget_released_tkn');
        let wgetGaCandidate = document.getElementById('wget_ga_candidate');
        let wgetTknMainContinuous = document.getElementById('wget_tkn_main_continuous');
        let wgetTknShipContinuous = document.getElementById('wget_tkn_ship_continuous');

        wgetAll.dataset.operation_key = 'tku_sync_packages';
        wgetReleasedTkn.dataset.operation_key = 'tku_sync_packages';
        wgetGaCandidate.dataset.operation_key = 'tku_sync_packages';
        wgetTknMainContinuous.dataset.operation_key = 'tku_sync_packages';
        wgetTknShipContinuous.dataset.operation_key = 'tku_sync_packages';

        wgetAll.modalId = 'wgetRefresh';
        wgetReleasedTkn.modalId = 'wgetRefresh';
        wgetGaCandidate.modalId = 'wgetRefresh';
        wgetTknMainContinuous.modalId = 'wgetRefresh';
        wgetTknShipContinuous.modalId = 'wgetRefresh';

        wgetAll.addEventListener('click', buttonActivationUpload);
        wgetReleasedTkn.addEventListener('click', buttonActivationUpload);
        wgetGaCandidate.addEventListener('click', buttonActivationUpload);
        wgetTknMainContinuous.addEventListener('click', buttonActivationUpload);
        wgetTknShipContinuous.addEventListener('click', buttonActivationUpload);

    });
});
