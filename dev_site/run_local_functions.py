if __name__ == "__main__":
    import logging
    import django
    import pytz
    import copy
    import collections
    import datetime
    from operator import itemgetter

    django.setup()

    from octo_tku_patterns.models import TestCases, TestCasesDetails

    log = logging.getLogger("octo.octologger")
    log.info("\n\n\n\n\nRun dev_site/run_local_functions.py")

    now = datetime.datetime.now(tz=pytz.utc)
    tomorrow = now + datetime.timedelta(days=1)
    queryset_all = TestCases.objects.all()

    exclude_changes = [
        '791013',
        '784570',
        '784672',
        '784741',
        '790845',
        '716460',  # TKN SHIP STARTED HERE
        '716461',
        '790846',
        '787058',
        '787059',
    ]


    def key_group(queryset):
        key_group_ = TestCasesDetails.objects.get(title__exact='key')
        included = key_group_.test_cases.values('id')
        key_cases = TestCases.objects.filter(id__in=included)
        queryset = queryset | key_cases
        return queryset


    def excluded_group(queryset):
        excluded_group_ = TestCasesDetails.objects.get(title__exact='excluded')
        excluded_ids = excluded_group_.test_cases.values('id')
        queryset = queryset.exclude(id__in=excluded_ids)
        return queryset


    def night_select(branch, queryset):
        date_from = now - datetime.timedelta(days=int(730))
        queryset = queryset.filter(change_time__range=[date_from, tomorrow])  # 1
        key_group(queryset)  # 2
        queryset = queryset.filter(tkn_branch__exact=branch)  # 3
        excluded_group(queryset)  # 4
        queryset = queryset.exclude(change__in=exclude_changes)  # 5
        return queryset

    # Explain and show query:
    selected_tkn_main = night_select('tkn_main', queryset_all)
    log.info(f"Explain QUERY for tkn_main: \ncount: {selected_tkn_main.count()} \nexplain: {selected_tkn_main.explain()} \nQUERY\n'''{selected_tkn_main.query}'''")
    selected_tkn_ship = night_select('tkn_ship', queryset_all)
    log.info(f"Explain QUERY for tkn_ship: \ncount: {selected_tkn_ship.count()} \nexplain: {selected_tkn_ship.explain()} \nQUERY\n'''{selected_tkn_ship.query}'''")

    # Show objects:
    shorten_tkn_main = selected_tkn_main.values('pattern_library', 'pattern_folder_name')
    log.debug(f"Shorten 'tkn_main' queryset with only few values: {shorten_tkn_main} \nQUERY\n'''{shorten_tkn_main.query}'''")
    shorten_tkn_ship = selected_tkn_ship.values('pattern_library', 'pattern_folder_name')
    log.debug(f"Shorten 'tkn_ship' queryset with only few values: {shorten_tkn_ship} \nQUERY\n'''{shorten_tkn_ship.query}'''")

    # Evaluate and make lists:
    l_tkn_main = list(shorten_tkn_main)
    # log.debug(f"Full list of selected: 'l_tkn_main' {len(l_tkn_main)}: {l_tkn_main}")
    l_tkn_ship = list(shorten_tkn_ship)
    # log.debug(f"Full list of selected: 'l_tkn_ship' {len(l_tkn_ship)}: {l_tkn_ship}")

    not_in_ship = []
    for item in l_tkn_main:
        if item not in l_tkn_ship:
            not_in_ship.append(item)
    log.debug(f"Cases are not in ship: {not_in_ship}")

