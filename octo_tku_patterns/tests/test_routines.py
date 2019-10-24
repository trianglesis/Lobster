"""
Testing ...
"""
from django.test import SimpleTestCase
from django.http import HttpRequest
from django.test import SimpleTestCase
from django.urls import reverse

from octo import views
from octo_tku_patterns.tasks import PatternRoutineCases


# class OctopusRoutinesTests(SimpleTestCase):
#
#     def setUpTestData(self):
#         # Test args
#         self.user_name = 'DjangoTest'  # ('user_name')
#         self.addm_group = None  # ('addm_group', None)
#         self.refresh = True  # ('refresh', None)
#         self.wipe = True  # ('wipe', None)
#         self.branch = 'tkn_main'  # ('branch')
#         self.pattern_library = 'CORE'  # ('pattern_library')
#         self.pattern_folder = '10genMongoDB'  # ('pattern_folder')
#         self.pattern_filename = '10genMongoDB'  # ('pattern_filename')
#         self.test_function = ''  # ('test_function', '')
#
#     def create_whatever(self):
#         return 'Hello test!'
#
#     def user_test_select_pattern_and_addm(self):
#
#         d_kwargs = dict(
#             user_name=self.user_name,
#             addm_group=self.addm_group,
#             refresh=self.refresh,
#             wipe=self.wipe,
#             branch=self.branch,
#             pattern_library=self.pattern_library,
#             pattern_folder=self.pattern_folder,
#             pattern_filename=self.pattern_filename,
#             test_function=self.test_function,
#         )
#
#         user_test = PatternRoutineCases.user_test(**d_kwargs)

class HomePageTests(SimpleTestCase):

    def test_home_page_status_code(self):
        response = self.client.get('/')
        self.assertEquals(response.status_code, 200)

    def test_view_url_by_name(self):
        response = self.client.get(reverse('home'))
        self.assertEquals(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('home'))
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_home_page_contains_correct_html(self):
        response = self.client.get('/')
        self.assertContains(response, '<h1>Homepage</h1>')

    def test_home_page_does_not_contain_incorrect_html(self):
        response = self.client.get('/')
        self.assertNotContains(
            response, 'Hi there! I should not be on the page.')