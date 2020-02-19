import os
from time import time
from queue import Queue
from threading import Thread
import argparse
import subprocess

"""
Use this to start/stop/restart celery, it's much more flexible.
TODO: Add restart for single worker only? Or maybe this is not the best approach?
TODO: Add some sort of log rotate?

/var/www/octopus/venv/bin/python3 /var/www/octopus/z_DEV/services/celery_services/celery_service_debug.py --mode=restart
venv/bin/celery flower --broker=amqp://octo_user:hPoNaEb7@localhost:5672/tentacle --broker_api=http://octo_user:hPoNaEb7@localhost:15672/api/

nssm.exe edit CELERY_routines && nssm.exe edit CELERY_alpha && nssm.exe edit CELERY_charlie && nssm.exe edit CELERY_golf && nssm.exe edit CELERY_parsing && nssm.exe edit CELERY_Flower

celery multi start w_parsing@tentacle -A octo.octo_celery:app --pidfile=/opt/celery/w_parsing@tentacle.pid --logfile=/var/log/octopus/w_parsing@tentacle.log --loglevel=INFO --concurrency=1 -E
celery -A octo w_parsing@tentacle --pidfile=/opt/celery/w_parsing@tentacle.pid --logfile=/var/log/octopus/w_parsing@tentacle.log --loglevel=INFO --concurrency=1 -E
"""

# CELERY_BIN = "/var/www/octopus/venv/bin/celery"
CELERY_APP = "octo.octo_celery:app"
CELERYD_PID_FILE = "/opt/celery/{PID}.pid"
CELERYD_LOG_FILE = "{PATH}/{LOG}.log"
CELERYD_LOG_LEVEL = "INFO"
CELERYD_OPTS = "--concurrency=1 -E"

CELERYD_NODES = [
    # "w_development@tentacle",
    "w_parsing@tentacle",
    "w_routines@tentacle",
    "alpha@tentacle",
    "beta@tentacle",
    # "charlie@tentacle",
    # "delta@tentacle",
    # "echo@tentacle",
    # "foxtrot@tentacle",
    # "golf@tentacle",
    # 'hotel@tentacle',
    # 'india@tentacle',
    # 'juliett@tentacle',
    # 'kilo@tentacle',
    # 'lima@tentacle',
    # 'mike@tentacle',
    # 'november@tentacle',
    # 'oskar@tentacle',
    # 'papa@tentacle',
    # 'quebec@tentacle',
    # 'romeo@tentacle',
]

# celery -A octo worker --loglevel=info
# celery -A octo w_parsing@tentacle --pidfile=/opt/celery/w_parsing@tentacle.pid --logfile=/var/log/octopus/w_parsing@tentacle.log --loglevel=info --concurrency=1 -E
commands_list_start = "{CELERY_BIN} multi start {celery_node} -A {CELERY_APP} --pidfile={CELERYD_PID_FILE} --logfile={CELERYD_LOG_FILE} --loglevel={CELERYD_LOG_LEVEL} {CELERYD_OPTS}"
commands_list_kill = "pkill -9 -f 'celery worker'"


def th_run(args):
    print(args)
    mode = args.mode
    env = args.env
    print('Run th_run')

    stat = dict(
        start=commands_list_start,
        kill=commands_list_kill,
    )
    celery_bin = dict(
        wsl_work='venv/bin/celery',
        wsl_home='',
        octopus='/var/www/octopus/venv/bin/celery',
        lobster='/var/www/octopus/venv/bin/celery',
    )
    CELERY_BIN = celery_bin[env]

    celery_logs = dict(
        wsl_work='/var/log/octopus',
        wsl_home='',
        octopus='/var/log/octopus',
        lobster='/var/log/octopus',
    )
    CELERY_LOG_PATH = celery_logs[env]

    cwd_path = dict(
        wsl_work='/mnt/d/perforce/addm/tkn_sandbox/o.danylchenko/projects/PycharmProjects/lobster/',
        wsl_home='',
        octopus='/var/www/octopus/',
        lobster='/var/www/octopus/',
    )

    ts = time()
    thread_list = []
    th_out = []
    test_q = Queue()

    for celery_node in CELERYD_NODES:
        cmd_draft = stat[mode]
        cmd = cmd_draft.format(
            CELERY_BIN=CELERY_BIN,
            celery_node=celery_node,
            CELERY_APP=CELERY_APP,
            CELERYD_PID_FILE=CELERYD_PID_FILE.format(PID=celery_node),
            CELERYD_LOG_FILE=CELERYD_LOG_FILE.format(PATH=CELERY_LOG_PATH, LOG=celery_node),
            CELERYD_LOG_LEVEL=CELERYD_LOG_LEVEL,
            CELERYD_OPTS=CELERYD_OPTS,
        )
        print(f"Run: {cmd}")
        args_d = dict(cmd=cmd, test_q=test_q, cwd=cwd_path[env])
        th_name = f"Run CMD: {cmd}"
        try:
            test_thread = Thread(target=worker_restart, name=th_name, kwargs=args_d)
            test_thread.start()
            thread_list.append(test_thread)
        except Exception as e:
            msg = "Thread test fail with error: {}".format(e)
            print(msg)
            return msg
    # Execute threads:
    for th in thread_list:
        th.join()
        th_out.append(test_q.get())
    print(f'All run Took {time() - ts} Out {th_out}')


def worker_restart(**args_d):
    cmd = args_d.get('cmd')
    cwd = args_d.get('cwd')
    test_q = args_d.get('test_q')
    my_env = os.environ.copy()
    run_results = []
    try:
        run_cmd = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   cwd=cwd,
                                   env=my_env,
                                   shell=True,
                                   )
        # run_cmd.wait()
        stdout, stderr = run_cmd.communicate()
        stdout, stderr = stdout.decode('utf-8'), stderr.decode('utf-8')
        run_results.append({'stdout': stdout, 'stderr': stderr})
        test_q.put(run_results)
    except Exception as e:
        msg = f"<=run_subprocess=> Error during operation for: {cmd} {e}"
        test_q.put(msg)
        print(msg)


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-m', '--mode', choices=['start', 'kill'], required=True)
parser.add_argument('-e', '--env', choices=['wsl_work', 'wsl_home', 'octopus', 'lobster'], required=True)
th_run(parser.parse_args())
