
import os
from time import time
from queue import Queue
from threading import Thread
import subprocess

"""
nssm.exe edit CELERY_routines && nssm.exe edit CELERY_alpha && nssm.exe edit CELERY_charlie && nssm.exe edit CELERY_golf && nssm.exe edit CELERY_parsing && nssm.exe edit CELERY_Flower
"""

commands_list = [
    'nssm.exe restart CELERY_routines',
    # 'nssm.exe stop CELERY_routines',
    # 'nssm.exe start CELERY_routines',
    # 'net stop CELERY_routines && net start CELERY_routines',

    'nssm.exe restart CELERY_alpha',
    # 'nssm.exe stop CELERY_alpha',
    # 'nssm.exe start CELERY_alpha',
    # 'net stop CELERY_alpha && net start CELERY_alpha',

    # 'nssm.exe restart CELERY_charlie',
    # 'nssm.exe stop CELERY_charlie',
    # 'nssm.exe start CELERY_charlie',
    # 'net stop CELERY_charlie && net start CELERY_charlie',

    'nssm.exe restart CELERY_golf',
    # 'nssm.exe stop CELERY_golf',
    # 'nssm.exe start CELERY_golf',
    # 'net stop CELERY_golf && net start CELERY_golf',

    # 'nssm.exe restart CELERY_parsing',
    # 'nssm.exe stop CELERY_parsing',
    # 'nssm.exe start CELERY_parsing',
    # 'net stop CELERY_parsing && net start CELERY_parsing',

    'nssm.exe restart CELERY_Flower',
    # 'nssm.exe stop CELERY_Flower',
    # 'nssm.exe start CELERY_Flower',
    # 'net stop CELERY_Flower && net start CELERY_Flower',
]


def th_run():
    print('Run th_run')
    ts = time()
    thread_list = []
    th_out = []
    test_q = Queue()

    for cmd in commands_list:
        args_d = dict(cmd=cmd, test_q=test_q)
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
    test_q = args_d.get('test_q')

    if "KBP1" in os.getenv('COMPUTERNAME', 'defaultValue'):
        octo_core = "D:\\perforce\\addm\\tkn_sandbox\\o.danylchenko\\projects\\PycharmProjects\\lobster"
    else:
        octo_core = "D:\\Projects\\PycharmProjects\\lobster\\"
    my_env = os.environ.copy()
    print(f"Run: {cmd}")

    run_results = []
    try:
        run_cmd = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   cwd=octo_core,
                                   env=my_env,
                                   )
        run_cmd.communicate()
        stdout, stderr = run_cmd.communicate()
        stdout, stderr = stdout.decode('utf-8'), stderr.decode('utf-8')
        run_cmd.wait()
        run_results.append({'stdout': stdout, 'stderr': stderr})
        test_q.put(run_results)
    except Exception as e:
        msg = f"<=run_subprocess=> Error during operation for: {cmd} {e}"
        test_q.put(msg)
        print(msg)


if __name__ == "main":
    th_run()

th_run()
