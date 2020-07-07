#!/usr/bin/env python
import os
import sys
import octo.config_cred as conf_cred
from octo import settings

if __name__ == "__main__":

    if conf_cred.DEV_HOST not in settings.CURR_HOSTNAME:
        print("Load prod octo.settings")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "octo.settings")
    else:
        print("WARNING: LOADING DEVELOPMENT SETTINGS - octo.win_settings!!!")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "octo.win_settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
