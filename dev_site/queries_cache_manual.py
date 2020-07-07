if __name__ == "__main__":
    from django.test import Client

    def main_pages_get_gen_cache():
        c = Client(
            SERVER_NAME='127.0.0.1',
            HTTP_USER_AGENT='Mozilla/5.0',
        )
        login = c.login(username='test', password='rQBzX5SveIokyF0uci5A')
        if login:
            print("User logged in - making request")
            # Main page:
            resp_main_page = c.get('/')
            print(f"Main page {resp_main_page.status_code}")
            # test_history_digest_today
            response_hist = c.get('/octo_tku_patterns/test_history_digest_today/', {'tkn_branch': 'tkn_main', 'tst_status': 'notpass'})
            print(f"Test history today: {response_hist.status_code} "
                  f"\nContext: {response_hist.context['object_list']}\nRequest: {response_hist.request}")

    main_pages_get_gen_cache()