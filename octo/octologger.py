"""
Octopus logger to track:
- all intra-operations
- all external operations
etc.
"""

import datetime
import logging
import os

now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
place = os.path.dirname(os.path.abspath(__file__))


def test_logger():
    """
    Create very detailed log for pattern testing.
    $ chgrp loggroup logdir
    $ chmod g+w logdir
    $ chmod g+s logdir
    $ usermod -a -G loggroup myuser
    $ umask 0002
    """

    """
    If you want to do custom logging, you should use the 
    folder /var/log/my-logs, to which you have full read/write access, including adding + deleting files....
    
    # getent group celery
    celery:x:1004:user,apache
    
    # getent group loggroup
    loggroup:x:1003:user,apache

    # getent group apache
    apache:x:48:

    usermod -a -G apache user
    
    """
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    log_name = "/var/log/octopus/WEB_octopus.log"

    # Extra detailed logging to file:
    f_handler = logging.FileHandler(log_name, mode='a', encoding='utf-8')

    f_handler.setLevel(logging.DEBUG)
    # Extra detailed logging to console:
    f_format = logging.Formatter(
        '{asctime:<24}'
        '{levelname:<8}'
        '{filename:<20}'
        '{funcName:<22}'
        'L:{lineno:<6}'
        '{message:8s}',
        style='{'
    )

    f_handler.setFormatter(f_format)
    log.addHandler(f_handler)

    return log
