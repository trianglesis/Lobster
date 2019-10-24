let select = document.getElementById('id_test_cases');
multi(select, {
    // enable search
    enable_search: true,
    // placeholder of search input
    search_placeholder: 'Search...',

    non_selected_header: null,
    selected_header: null
});