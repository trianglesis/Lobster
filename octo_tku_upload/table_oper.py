"""
Store here local functions to parse, obtain, compose operations for database details.
"""
import datetime
from django.db.models import Max

from octo_tku_upload.models import UploadTestsNew
from octo_tku_upload.models import UploadTests as OldUploadTests
from octo_tku_upload.models import TkuPackagesNew as TkuPackages


# Python logger
import logging
log = logging.getLogger("octo.octologger")


class UploadTKUTableOper:

    @staticmethod
    def select_packages_narrow(addm_item=None, tku_type=None, package_type=None):
        """
        Select package for TKU upload test:
        - main option is based on package type - arg 'tku_type'
        - of no 'tku_type' - use arg 'package_type'
        - if no option set - return latest GA

        :param package_type: TKN_release_2018-09-1-113, tkn_main_continuous_2068-11-1-000, addm_released_2018-02-3-000
        :param tku_type: ga_candidate, addm_released, released_tkn, tkn_main_continuous
        :param addm_item: addm version int to select TKU zip
        :return:
        """
        if addm_item:
            if tku_type and not package_type:
                # Select latest build fot tku_type:
                tku_type_max = TkuPackages.objects.filter(tku_type__exact=tku_type).aggregate(Max('package_type'))
                return TkuPackages.objects.filter(
                    tku_type__exact=tku_type,
                    addm_version__exact=addm_item['addm_v_int'],
                    package_type__exact=tku_type_max['package_type__max']).values()

            elif tku_type and package_type:
                # Select exact tku_type and package type:
                return TkuPackages.objects.filter(
                    tku_type__exact=tku_type,
                    package_type__exact=package_type,
                    addm_version__exact=addm_item['addm_v_int']).values()

            elif not tku_type and package_type:
                # Select exact package type:
                return TkuPackages.objects.filter(
                    package_type__exact=package_type,
                    addm_version__exact=addm_item['addm_v_int']).values()

            else:
                # Select latest GA build, by default:
                ga_candidate_max = TkuPackages.objects.filter(tku_type__exact='ga_candidate').aggregate(Max('package_type'))
                return TkuPackages.objects.filter(
                    tku_type__exact='ga_candidate',
                    addm_version__exact=addm_item['addm_v_int'],
                    package_type__exact=ga_candidate_max['package_type__max']).values()
        else:
            if tku_type and not package_type:
                # Select latest build fot tku_type:
                tku_type_max = TkuPackages.objects.filter(tku_type__exact=tku_type).aggregate(Max('package_type'))
                return TkuPackages.objects.filter(
                    tku_type__exact=tku_type,
                    package_type__exact=tku_type_max['package_type__max']).values()
            elif tku_type and package_type:
                # Select exact tku_type and package type:
                return TkuPackages.objects.filter(
                    tku_type__exact=tku_type,
                    package_type__exact=package_type).values()
            elif not tku_type and package_type:
                # Select exact package type:
                return TkuPackages.objects.filter(
                    package_type__exact=package_type).values()
            else:
                # Select latest GA build, by default:
                ga_candidate_max = TkuPackages.objects.filter(tku_type__exact='ga_candidate').aggregate(Max('package_type'))
                return TkuPackages.objects.filter(
                    tku_type__exact='ga_candidate',
                    package_type__exact=ga_candidate_max['package_type__max']).values()

    @staticmethod
    def select_tku_packages(query_args):
        tku_packages = []
        ga_candidate_max = TkuPackages.objects.filter(tku_type__exact='ga_candidate').aggregate(Max('package_type'))
        released_tkn_max = TkuPackages.objects.filter(tku_type__exact='released_tkn').aggregate(Max('package_type'))
        tkn_main_continuous_max = TkuPackages.objects.filter(tku_type__exact='tkn_main_continuous').aggregate(Max('package_type'))

        if query_args:
            if query_args.get('tku_type'):
                tku_packages = TkuPackages.objects.filter(tku_type__exact=query_args['tku_type']).order_by('package_type')
            else:
                tku_packages = TkuPackages.objects.order_by('tku_type', 'package_type')

        return tku_packages, ga_candidate_max, released_tkn_max, tkn_main_continuous_max

    @staticmethod
    def select_tku_update_digest(mode_key=None):
        """
        Select two steps of TKU upgrade test.
        Filter latest MAX package type, or date?

        Firstly - get max package type:
        aggr_max: {'package_type__max': 'tkn_main_continuous_2069-03-1-000'}

        Secondly - get that package last date record
        Newest latest_date: {'test_date_time__max':
            datetime.datetime(2019, 3, 21, 15, 14, 27, 219127, tzinfo=<UTC>)}

        Then get upload test records corresponding that package max value and date of tests.
            Date choose BETWEEN latest and today (SQL="BETWEEN '2019-03-21' AND '2019-03-24'")

        :return:
        """
        if not mode_key:
            mode_key = 'tkn_ship_continuous_install'
        # Get package type max version:
        aggr_max = UploadTestsNew.objects.filter(mode_key__exact=mode_key).aggregate(Max('package_type'))
        # Get this package only newest day record:
        latest_date = UploadTestsNew.objects.filter(
            mode_key__exact=mode_key,
            package_type=aggr_max['package_type__max']).aggregate(Max('test_date_time'))

        if latest_date['test_date_time__max']:
            latest_date = latest_date['test_date_time__max'].strftime('%Y-%m-%d')
        else:
            latest_date = datetime.datetime.now().strftime('%Y-%m-%d')

        tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)
        current_date = tomorrow.strftime('%Y-%m-%d')

        upload_test_log = UploadTestsNew.objects.filter(
            test_date_time__range=[latest_date, current_date],
            mode_key__exact=mode_key,
            package_type__exact=aggr_max['package_type__max'],
        )
        # log.debug("MODE_KEY: %s Package found MAX: %s DATE: %s", mode_key, aggr_max, latest_date)
        # log.debug("<=Django QUERY=> select_tku_update_digest: \n%s", upload_test_log.query)
        return upload_test_log
