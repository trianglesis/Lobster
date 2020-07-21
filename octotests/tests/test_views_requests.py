import logging
import unittest
from django.test import Client

from django.test import RequestFactory, TestCase
from datetime import date, datetime, timedelta

from octo.views import *
from octo_tku_patterns.views import *
from octo_tku_upload.views import *

from octo.cache import OctoCache

log = logging.getLogger("octo.octologger")


class SimpleTest(unittest.TestCase):
    def setUp(self):
        # Every test needs a client.
        self.client = Client(
            SERVER_NAME='127.0.0.1',
            HTTP_USER_AGENT='Mozilla/5.0',
        )
        login = self.client.login(username='test', password='rQBzX5SveIokyF0uci5A')
        self.assertTrue(login)
        self.tkn_branches = [
            'tkn_main',
            'tkn_ship',
        ]
        self.test_statuses = [
            'pass',
            'fail',
            'notpass',
            'error',
            'skip',
        ]
        self.addm_names = [
            'custard_cream',
            'double_decker',
            'fish_finger',
        ]
        self.pattern_libraries = [
            'BLADE_ENCLOSURE',
            'CLOUD',
            'CORE',
            'DBDETAILS',
            'LOAD_BALANCER',
            'MANAGEMENT_CONTROLLERS',
            'MIDDLEWAREDETAILS',
            'NETWORK',
            'STORAGE',
            'SYSTEM',
        ]

    def test001_main_page(self):
        """
        Testing main page load and cache
        :return:
        """
        log.info("Running: test001_main_page")
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test001_addm_digest(self):
        """
        ADDM Digest load and cache
        :return:
        """
        log.info("Running: test001_addm_digest")
        response = self.client.get('/octo_tku_patterns/addm_digest/')
        self.assertEqual(response.status_code, 200)

    def test001_tku_workbench(self):
        """
        Workbench of TKU Uploads
        :return:
        """
        log.info("Running: test001_tku_workbench")
        response = self.client.get('/octo_tku_upload/tku_workbench/')
        self.assertEqual(response.status_code, 200)

    def test001_upload_today(self):
        """
        TKU Upload today page test and cache
        :return:
        """
        log.info("Running: test007_upload_today")
        response = self.client.get('/octo_tku_upload/upload_today/')
        self.assertEqual(response.status_code, 200)

    def test002_tests_last(self):
        """
        Get most common views on tests_last for different branches and all test statuses
        Those are dynamical views all ADDMs on one, but template and JS sorting.
        Maybe do not load a LIBRARY related, usually it does not so needed for users to be so fast.
        :return:
        """
        log.info("Running: test004_tests_last")
        pages = 0
        for branch in self.tkn_branches:
            for status in self.test_statuses:
                response = self.client.get('/octo_tku_patterns/tests_last/',
                                           {'tkn_branch': branch, 'tst_status': status})
                self.assertEqual(response.status_code, 200)
                pages += 1
        log.info(f'Tested {pages} pages.')

    def test003_test_details(self):
        """
        Get most common views on /octo_tku_patterns/test_details
        Most pages which opens when clicking on count of passed,failed,errored tests
        :return:
        """
        pages = 0
        for branch in self.tkn_branches:
            for addm_name in self.addm_names:
                for status in self.test_statuses:
                    response = self.client.get(
                        '/octo_tku_patterns/test_details/',
                        {'tkn_branch': branch, 'addm_name': addm_name, 'tst_status': status})
                    self.assertEqual(response.status_code, 200)
                    pages += 1
        log.info(f'Tested {pages} pages.')

    def test004_test_history_digest_today(self):
        """
        Hostory digest today - test and generate cache for branches and most useful test statuses, not passed, skipped or all.
        :return:
        """
        log.info("Running: test005_test_history_digest_today")
        pages = 0
        for branch in self.tkn_branches:
            for status in ['fail', 'notpass', 'error', ]:
                response = self.client.get('/octo_tku_patterns/test_history_digest_today/',
                                           {'tkn_branch': branch, 'tst_status': status})
                self.assertEqual(response.status_code, 200)
                pages += 1
        log.info(f'Tested {pages} pages.')

    def test008_test_cases(self):
        """
        Test cases view - load both branches and all libraries. Then load a night run query.
        :return:
        """
        log.info("Running: test008_test_cases")
        pages = 0
        response = self.client.get('/octo_tku_patterns/test_cases/')
        self.assertEqual(response.status_code, 200)
        pages += 1
        for branch in self.tkn_branches:
            for library in self.pattern_libraries:
                response = self.client.get('/octo_tku_patterns/test_cases/',
                                           {'tkn_branch': branch, 'pattern_library': library})
                self.assertEqual(response.status_code, 200)
                pages += 1
        # Load view for night test run:
        response = self.client.get('/octo_tku_patterns/test_cases/', {'last_days': 90})
        self.assertEqual(response.status_code, 200)
        pages += 1
        log.info(f'Tested {pages} pages.')

    def test009_test_history_digest_day(self):
        log.info("Running: test009_test_history_digest_day")
        pages = 0
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%b')
        day = now.strftime('%d')
        day_1 = (now - timedelta(days=1)).strftime('%d')
        day_2 = (now - timedelta(days=2)).strftime('%d')
        day_3 = (now - timedelta(days=3)).strftime('%d')

        for branch in self.tkn_branches:
            for _day in [day, day_1, day_2, day_3]:
                test_url = f'/octo_tku_patterns/test_history_digest_day/{year}/{month}/{_day}'
                attrs = {'tkn_branch': branch, 'tst_status': 'notpass'}
                response = self.client.get(test_url, attrs, follow=True)
                self.assertEqual(response.status_code, 200)
                log.info(response.redirect_chain)
                pages += 1
        log.info(f'Tested {pages} pages.')


class AdvancedViews(TestCase):
    """
    https://docs.djangoproject.com/en/3.0/topics/testing/advanced/#django.test.RequestFactory
    """
    def setUp(self):
        self.request = RequestFactory()
        self.tkn_branches = [
            'tkn_main',
            'tkn_ship',
        ]
        self.test_statuses = [
            'pass',
            'fail',
            'notpass',
            'error',
            'skip',
        ]
        self.addm_names = [
            'custard_cream',
            'double_decker',
            'fish_finger',
        ]
        self.pattern_libraries = [
            'BLADE_ENCLOSURE',
            'CLOUD',
            'CORE',
            'DBDETAILS',
            'LOAD_BALANCER',
            'MANAGEMENT_CONTROLLERS',
            'MIDDLEWAREDETAILS',
            'NETWORK',
            'STORAGE',
            'SYSTEM',
        ]

    def test001_main_page(self):
        """
        Testing main page load and cache
        :return:
        """
        log.info("Running: test001_main_page")
        view = MainPage()
        request = self.request.get('/')
        view.setup(request)
        view.get(request)

    def test001_addm_digest(self):
        """
        ADDM Digest load and cache
        :return:
        """
        log.info("Running: test001_addm_digest")
        view = AddmDigestListView()
        request = self.request.get('/octo_tku_patterns/addm_digest/')
        view.setup(request)
        view.get(request)

    def test001_tku_workbench(self):
        """
        Workbench of TKU Uploads
        :return:
        """
        log.info("Running: test001_tku_workbench")
        view = TKUUpdateWorkbenchView()
        request = self.request.get('/octo_tku_upload/tku_workbench/')
        view.setup(request)
        view.get(request)

    def test001_upload_today(self):
        """
        TKU Upload today page test and cache
        :return:
        """
        log.info("Running: test001_upload_today")
        view = UploadTestTodayArchiveView()
        request = self.request.get('/octo_tku_upload/upload_today/')
        view.setup(request)
        queryset = view.get_queryset()
        OctoCache().cache_query(queryset)
        view.get(request)

    def test002_tests_last(self):
        """
        Get most common views on tests_last for different branches and all test statuses
        Those are dynamical views all ADDMs on one, but template and JS sorting.
        Maybe do not load a LIBRARY related, usually it does not so needed for users to be so fast.
        :return:
        """
        log.info("Running: test002_tests_last")
        pages = 0
        view = TestLastDigestListView()
        for branch in self.tkn_branches:
            for status in self.test_statuses:
                request = self.request.get('/octo_tku_patterns/tests_last/',
                                           {'tkn_branch': branch, 'tst_status': status})
                view.setup(request)
                queryset = view.get_queryset()
                OctoCache().cache_query(queryset)
                # view.options(request)
                view.get(request)
                pages += 1
        log.info(f'Tested {pages} pages.')

    def test002_tests_last_tkn_main(self):
        """
        Get most common views on tests_last for different branches and all test statuses
        Those are dynamical views all ADDMs on one, but template and JS sorting.
        Maybe do not load a LIBRARY related, usually it does not so needed for users to be so fast.
        :return:
        """
        log.info("Running: test002_tests_last_tkn_main")
        view = TestLastDigestListView()
        request = self.request.get('/octo_tku_patterns/tests_last/',
                                   {'tkn_branch': 'tkn_main', 'tst_status': 'notpass'})
        view.setup(request)
        queryset = view.get_queryset()
        OctoCache().cache_query(queryset)
        # view.options(request)
        view.get(request)

    def test002_tests_last_tkn_ship(self):
        """
        Get most common views on tests_last for different branches and all test statuses
        Those are dynamical views all ADDMs on one, but template and JS sorting.
        Maybe do not load a LIBRARY related, usually it does not so needed for users to be so fast.
        :return:
        """
        log.info("Running: test002_tests_last_tkn_ship")
        view = TestLastDigestListView()
        request = self.request.get('/octo_tku_patterns/tests_last/',
                                   {'tkn_branch': 'tkn_ship', 'tst_status': 'notpass'})
        view.setup(request)
        queryset = view.get_queryset()
        OctoCache().cache_query(queryset)
        # view.options(request)
        view.get(request)

    def test003_test_details(self):
        """
        Get most common views on /octo_tku_patterns/test_details
        Most pages which opens when clicking on count of passed,failed,errored tests
        :return:
        """
        log.info("Running: test003_test_details")
        pages = 0
        view = TestLastSingleDetailedListView()
        for branch in self.tkn_branches:
            for addm_name in self.addm_names:
                for status in self.test_statuses:
                    request = self.request.get(
                        '/octo_tku_patterns/test_details/',
                        {'tkn_branch': branch, 'addm_name': addm_name, 'tst_status': status})
                    view.setup(request)
                    queryset = view.get_queryset()
                    OctoCache().cache_query(queryset)
                    view.get(request)
                    pages += 1
        log.info(f'Tested {pages} pages.')

    def test003_test_details_tkn_main(self):
        """
        Get most common views on /octo_tku_patterns/test_details
        Most pages which opens when clicking on count of passed,failed,errored tests
        :return:
        """
        log.info("Running: test003_test_details_tkn_main")
        pages = 0
        view = TestLastSingleDetailedListView()
        for addm_name in self.addm_names:
            request = self.request.get(
                '/octo_tku_patterns/test_details/',
                {'tkn_branch': 'tkn_main', 'addm_name': addm_name, 'tst_status': 'notpass'})
            view.setup(request)
            queryset = view.get_queryset()
            OctoCache().cache_query(queryset)
            view.get(request)
            pages += 1
        log.info(f'Tested {pages} pages.')

    def test003_test_details_tkn_ship(self):
        """
        Get most common views on /octo_tku_patterns/test_details
        Most pages which opens when clicking on count of passed,failed,errored tests
        :return:
        """
        log.info("Running: test003_test_details_tkn_ship")
        pages = 0
        view = TestLastSingleDetailedListView()
        for addm_name in self.addm_names:
            request = self.request.get(
                '/octo_tku_patterns/test_details/',
                {'tkn_branch': 'tkn_ship', 'addm_name': addm_name, 'tst_status': 'notpass'})
            view.setup(request)
            queryset = view.get_queryset()
            OctoCache().cache_query(queryset)
            view.get(request)
            pages += 1
        log.info(f'Tested {pages} pages.')

    def test002_test_cases(self):
        """
        Test cases view - load both branches and all libraries. Then load a night run query.
        :return:
        """
        log.info("Running: test008_test_cases")
        pages = 0
        view = TestCasesListView()
        # Solo
        request = self.request.get('/octo_tku_patterns/test_cases/')
        view.setup(request)
        queryset = view.get_queryset()
        OctoCache().cache_query(queryset)
        view.get(request)
        pages += 1
        # With args
        for branch in self.tkn_branches:
            for library in self.pattern_libraries:
                request = self.request.get('/octo_tku_patterns/test_cases/',
                                           {'tkn_branch': branch, 'pattern_library': library})
                view.setup(request)
                queryset = view.get_queryset()
                OctoCache().cache_query(queryset)
                view.get(request)
                pages += 1
        # Load view for night test run:
        request = self.request.get('/octo_tku_patterns/test_cases/', {'last_days': 90})
        view.setup(request)
        queryset = view.get_queryset()
        OctoCache().cache_query(queryset)
        view.get(request)
        pages += 1
        log.info(f'Tested {pages} pages.')

    def test004_test_history_digest_today(self):
        """
        Hostory digest today - test and generate cache for branches and most useful test statuses, not passed, skipped or all.
        :return:
        """
        log.info("Running: test004_test_history_digest_today")
        pages = 0
        view = TestHistoryDigestTodayView()
        for branch in self.tkn_branches:
            for status in ['fail', 'notpass', 'error', ]:
                request = self.request.get('/octo_tku_patterns/test_history_digest_today/',
                                           {'tkn_branch': branch, 'tst_status': status})
                view.setup(request)
                queryset = view.get_queryset()
                OctoCache().cache_query(queryset)
                view.get(request)
                pages += 1
        log.info(f'Tested {pages} pages.')

    def test004_test_history_digest_day(self):
        """
        Too slow?
        :return:
        """
        log.info("Running: test009_test_history_digest_day")
        pages = 0
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%b')
        day = now.strftime('%d')
        day_1 = (now - timedelta(days=1)).strftime('%d')
        day_2 = (now - timedelta(days=2)).strftime('%d')
        day_3 = (now - timedelta(days=3)).strftime('%d')
        view = TestHistoryDigestDailyView()

        for branch in self.tkn_branches:
            for _day in [day, day_1, day_2, day_3]:
                test_url = f'/octo_tku_patterns/test_history_digest_day/{year}/{month}/{_day}'
                attrs = {'tkn_branch': branch, 'tst_status': 'notpass'}
                request = self.request.get(test_url, attrs, follow=True)
                view.setup(request)
                queryset = view.get_queryset()
                OctoCache().cache_query(queryset)
                # view.get(request)
                pages += 1
        log.info(f'Tested {pages} pages.')


if __name__ == "__main__":
    unittest.main()
