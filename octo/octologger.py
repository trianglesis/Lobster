"""
Octopus logger to track:
- all intra-operations
- all external operations
etc.
"""


import datetime
import logging
from logging import handlers
import sys
import os
from os import stat

now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
place = os.path.dirname(os.path.abspath(__file__))


class GroupWriteRotatingFileHandler(handlers.RotatingFileHandler):

    def doRollover(self):
        """
        Override base class method to make the new log file group writable.
        https://stackoverflow.com/questions/1407474/does-python-logging-handlers-rotatingfilehandler-allow-creation-of-a-group-writa
        """
        # Rotate the file first.
        handlers.RotatingFileHandler.doRollover(self)

        # Add group write to the current permissions.
        currMode = os.stat(self.baseFilename).st_mode
        # noinspection PyUnresolvedReferences
        os.chmod(self.baseFilename, currMode | stat.S_IWGRP)


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

    if os.name == "nt":
        log_name = "WEB_octopus.log"
        cons_handler = logging.StreamHandler(stream=sys.stdout)
        cons_handler.setLevel(logging.DEBUG)
        cons_format = logging.Formatter('%(asctime)-24s'
                                        '%(levelname)-8s'
                                        '%(module)-20s'
                                        '%(funcName)-22s'
                                        'L:%(lineno)-6s'
                                        '%(message)8s')
        cons_handler.setFormatter(cons_format)
        log.addHandler(cons_handler)
    else:
        log_name = "/var/log/octopus/WEB_octopus.log"

    # Extra detailed logging to file:
    f_handler = logging.FileHandler(log_name, mode='a', encoding='utf-8',)

    f_handler.setLevel(logging.DEBUG)
    # Extra detailed logging to console:
    f_format = logging.Formatter('%(asctime)-24s'
                                 '%(levelname)-8s'
                                 '%(filename)-23s'
                                 '%(funcName)-26s'
                                 'L:%(lineno)-6s'
                                 '%(message)8s')

    f_handler.setFormatter(f_format)
    log.addHandler(f_handler)

    return log


# noinspection PyUnresolvedReferences
def dev_logger(custom_attr):
    log_place = os.path.join(os.path.dirname(place), 'log/')
    log_name = "{0}_DEV_{1}.log".format(log_place, custom_attr)

    log = logging.getLogger('TestLog')
    log.setLevel(logging.DEBUG)

    # Extra detailed logging to file:
    f_handler = logging.FileHandler(log_name, mode='a', encoding='utf-8')
    f_handler.setLevel(logging.DEBUG)

    f_format = logging.Formatter('%(asctime)-24s'
                                 '%(thread)d'
                                 '%(threadName)-8s'
                                 '%(levelname)-8s '
                                 '%(filename)-23s'
                                 '%(funcName)-22s'
                                 'L:%(lineno)-6s'
                                 '%(message)8s')
    f_handler.setFormatter(f_format)

    log.addHandler(f_handler)

    return log
