
import os
from time import time
from queue import Queue
from threading import Thread
import subprocess

commands_list = [
    'nssm.exe restart CELERY_routines',
    'nssm.exe restart CELERY_alpha',
    'nssm.exe restart CELERY_charlie',
    'nssm.exe restart CELERY_golf',
    'nssm.exe restart CELERY_parsing',
    'nssm.exe restart CELERY_Flower',
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
