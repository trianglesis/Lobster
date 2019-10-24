"""
URLs for module which select and show all data.
"""

from django.conf.urls import url
from selector_out.views import Searches

urlpatterns = [
    # Searches:
    url(r'^search_history/', Searches.search_history,
        name="search_history"),
    url(r'^search_history_results/', Searches.search_history,
        name="search_history_results"),
    # History select:
    url(r'^history_select/', Searches.history_select,
        name='history_select'),
    url(r'^global_search/', Searches.global_search,
        name='global_search'),
    url(r'^full_history/', Searches.full_history,
        name='full_history'),

]
