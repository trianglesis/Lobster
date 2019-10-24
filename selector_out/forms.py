"""
Here work on forms and execute database select on custom queries.
"""

import datetime
from django import forms
# from django.core.validators import MinValueValidator, MaxValueValidator
# Python logger
import logging
log = logging.getLogger("octo.octologger")

# Rubbish logger
# from octo.octologger import test_logger
# log = test_logger()


TEST_TABLE = (
    ('test_history', 'History',),
    ('test_latest', 'Latest',),
)

TKN_BRANCH = (
    ('tkn_main', 'Main',),
    ('tkn_ship', 'Ship',),
)
ADDM_NAMES = (
    ('double_decker', '11.3 double_decker',),
    ('custard_cream', '11.2 custard_cream',),
    ('bobblehat', '11.1 bobblehat',),
    ('aardvark', '11.0 aardvark',),
    ('zythum', '10.2 zythum',),
    # ('all_addms', 'Select all',)
)
DB_ATTRIBUTES = (
    ('pattern_folder_name', 'Pattern folder',),
    ('pattern_file_name', 'Pattern file name',),
)

PATTERN_LIBRARY = (
    ('CORE', 'CORE',),
    ('BLADE_ENCLOSURE', 'BLADE_ENCLOSURE',),
    ('CLOUD', 'CLOUD',),
    ('DBDETAILS', 'DBDETAILS',),
    ('EXTRAS', 'EXTRAS',),
    ('LOAD_BALANCER', 'LOAD_BALANCER',),
    ('MANAGEMENT_CONTROLLERS', 'MANAGEMENT_CONTROLLERS',),
    ('MIDDLEWAREDETAILS', 'MIDDLEWAREDETAILS',),
    ('NETWORK', 'NETWORK',),
    ('STORAGE', 'STORAGE',),
    ('SYSTEM', 'SYSTEM',),
)

LOG_STATUS = (
    ('not_pass_only', 'Not pass only',),
    ('error', 'Errors only',),
    ('skipped', 'Skipped only',),
    ('passed', 'Passed OK only',),
    ('fail', 'Failed only',),
    ('all', 'Everything',),
)


class TestRequest(forms.Form):
    """
    Add verify later
    """
    test_latest_hist = forms.ChoiceField(
        label='test_latest_hist',
        required=True,
        widget=forms.Select(attrs={'required': '', 'class': 'mr-sm-2 custom-select mb-2 mr-sm-2 mb-sm-0'}),
        choices=TEST_TABLE)

    tkn_branch_select = forms.ChoiceField(
        label='tkn_branch_select',
        required=True,
        widget=forms.Select(attrs={'required': '', 'class': 'mr-sm-2 custom-select mb-2 mr-sm-2 mb-sm-0'}),
        choices=TKN_BRANCH)

    addm_name_select = forms.ChoiceField(
        label='addm_name_select',
        required=True,
        widget=forms.Select(attrs={'required': '', 'class': 'mr-sm-2 custom-select mb-2 mr-sm-2 mb-sm-0'}),
        choices=ADDM_NAMES)

    select_attribute = forms.ChoiceField(
        label='select_attribute',
        required=True,
        widget=forms.Select(attrs={'required': '', 'class': 'mr-sm-2 custom-select mb-2 mr-sm-2 mb-sm-0'}),
        choices=DB_ATTRIBUTES)

    value_to_select = forms.CharField(
        label='value_to_select',
        required=True,
        widget=forms.TextInput(attrs={'class': 'mr-sm-2 form-control mb-2 mr-sm-2 mb-sm-0'}))

    date_from = forms.DateField(
        label='date_from',
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control col-form-label mb-2 mr-sm-2 mb-sm-0', 'type': 'date'}))


class DevTestRequest(forms.Form):
    """
    Add verify later
    """
    date_today = datetime.datetime.now()

    tkn_branch_select = forms.ChoiceField(
        label='tkn_branch_select',
        required=True,
        widget=forms.RadioSelect(
            attrs={
                'id': 'tkn_branch_select',
                'required': '',
            }
        ),
        initial=TKN_BRANCH[0][0],
        choices=TKN_BRANCH)

    addm_name_select = forms.ChoiceField(
        label='addm_name_select',
        required=True,
        widget=forms.RadioSelect(
            attrs={
                'id': 'addm_name_select',
                'required': '',
            }
        ),
        initial=ADDM_NAMES[0][0],
        choices=ADDM_NAMES)

    pattern_library_drop = forms.ChoiceField(
        label='pattern_library_drop',
        required=True,
        widget=forms.Select(
            attrs={
                'class': 'custom-select',
                'id': 'pattern_library',
                'required': '',
            }
        ),
        initial=PATTERN_LIBRARY[0][0],
        choices=PATTERN_LIBRARY)

    log_status = forms.ChoiceField(
        label='log_status',
        required=True,
        widget=forms.RadioSelect(
            attrs={
                'id': 'log_status',
                'required': '',
            }
        ),
        initial=LOG_STATUS[0][0],
        choices=LOG_STATUS)

    pattern_folder = forms.CharField(
        label='pattern_folder',
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'type': 'text',
                'id': 'pattern_folder',
                # 'required': '',
            },
        ),
        initial='.'
    )

    date_from = forms.DateField(
        label='date_from',
        required=True,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
                'required': '',
            },
        ),
        initial=date_today - datetime.timedelta(days=1)
    )

    date_to = forms.DateField(
        label='date_to',
        required=True,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
                'required': '',
            }
        ),
        initial=datetime.date.today
    )


class TestPastDays(forms.Form):
    """
    Browse days in the past
    """
    date_from = forms.DateField(
        label='date_from',
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control col-form-label mb-2 mr-sm-2 mb-sm-0', 'type': 'date'}))

    date_to = forms.DateField(
        label='date_from',
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control col-form-label mb-2 mr-sm-2 mb-sm-0', 'type': 'date'}))


class PatternChanges(forms.Form):
    """
    Select options to show table of patterns which corresponds some params

    """
    date_from = forms.DateField(
        label='date_from',
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control col-form-label mb-2 mr-sm-2 mb-sm-0', 'type': 'date'}))

    tkn_branch_select = forms.ChoiceField(
        label='tkn_branch_select',
        required=True,
        widget=forms.Select(attrs={'required': '', 'class': 'mr-sm-2 custom-select mb-2 mr-sm-2 mb-sm-0'}),
        choices=TKN_BRANCH)

    key_patterns_box = forms.CheckboxInput()


class GlobalSearch(forms.Form):
    search_string = forms.CharField(
        label='search_string',
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'type': 'text',
                'id': 'search_string',
                'placeholder': 'Search',
                'aria-label': 'Search',
            },
        ),
        # initial='AtlassianJIRA'
    )


# TEST FOR CELERY:
