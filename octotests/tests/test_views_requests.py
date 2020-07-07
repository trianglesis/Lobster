import unittest
from django.test import Client
from datetime import date, datetime, timedelta

class SimpleTest(unittest.TestCase):
    def setUp(self):
        # Every test needs a client.
        self.client = Client(
            SERVER_NAME='127.0.0.1',
            HTTP_USER_AGENT='Mozilla/5.0',
        )
        login = self.client.login(username='test', password='rQBzX5SveIokyF0uci5A')
        self.assertTrue(login)

    def test002_main_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test003_addm_digest(self):
        response = self.client.get('/octo_tku_patterns/addm_digest/')
        self.assertEqual(response.status_code, 200)

    def test004_tests_last(self):
        # Non pass
        response = self.client.get('/octo_tku_patterns/tests_last/', {'tkn_branch': 'tkn_main', 'tst_status': 'notpass'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/tests_last/', {'tkn_branch': 'tkn_ship', 'tst_status': 'notpass'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/tests_last/', {'tst_status': 'notpass'})
        self.assertEqual(response.status_code, 200)
        #  All
        response = self.client.get('/octo_tku_patterns/tests_last/', {'tkn_branch': 'tkn_main'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/tests_last/', {'tkn_branch': 'tkn_ship'})
        self.assertEqual(response.status_code, 200)


        response = self.client.get('/octo_tku_patterns/tests_last/', {'test_type': 'product_content'})
        self.assertEqual(response.status_code, 200)

    def test005_test_history_digest_today(self):
        response = self.client.get('/octo_tku_patterns/test_history_digest_today/', {'tkn_branch': 'tkn_main', 'tst_status': 'notpass'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_history_digest_today/', {'tkn_branch': 'tkn_ship', 'tst_status': 'notpass'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_history_digest_today/', {'tst_status': 'notpass'})
        self.assertEqual(response.status_code, 200)

    def test008_tku_workbench(self):
        response = self.client.get('/octo_tku_upload/tku_workbench/')
        self.assertEqual(response.status_code, 200)

    def test007_upload_today(self):
        response = self.client.get('/octo_tku_upload/upload_today/')
        self.assertEqual(response.status_code, 200)

    def test008_test_cases(self):
        response = self.client.get('/octo_tku_patterns/test_cases/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_cases/', {'tkn_branch': 'tkn_main',})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_cases/', {'tkn_branch': 'tkn_ship',})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_cases/', {'pattern_library': 'BLADE_ENCLOSURE'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_cases/', {'pattern_library': 'CLOUD'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_cases/', {'pattern_library': 'CORE'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_cases/', {'pattern_library': 'LOAD_BALANCER'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_cases/', {'pattern_library': 'NETWORK'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_cases/', {'pattern_library': 'STORAGE'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/octo_tku_patterns/test_cases/', {'pattern_library': 'MANAGEMENT_CONTROLLERS'})
        self.assertEqual(response.status_code, 200)

    def test009_test_history_digest_day(self):
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%b')
        day = now.strftime('%d')
        day_1 = (now - timedelta(days=1)).strftime('%d')
        day_2 = (now - timedelta(days=2)).strftime('%d')
        day_3 = (now - timedelta(days=3)).strftime('%d')

        test_url = f'/octo_tku_patterns/test_history_digest_day/{year}/{month}/{day}'
        response = self.client.get(test_url, {'tkn_branch': 'tkn_main', 'tst_status': 'notpass'}, follow=True)
        print(response.redirect_chain)
        self.assertEqual(response.status_code, 200)

        test_url = f'/octo_tku_patterns/test_history_digest_day/{year}/{month}/{day_1}'
        response = self.client.get(test_url, {'tkn_branch': 'tkn_main', 'tst_status': 'notpass'}, follow=True)
        print(response.redirect_chain)
        self.assertEqual(response.status_code, 200)

        test_url = f'/octo_tku_patterns/test_history_digest_day/{year}/{month}/{day_2}'
        response = self.client.get(test_url, {'tkn_branch': 'tkn_main', 'tst_status': 'notpass'}, follow=True)
        print(response.redirect_chain)
        self.assertEqual(response.status_code, 200)

        test_url = f'/octo_tku_patterns/test_history_digest_day/{year}/{month}/{day_3}'
        response = self.client.get(test_url, {'tkn_branch': 'tkn_main', 'tst_status': 'notpass'}, follow=True)
        print(response.redirect_chain)
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()