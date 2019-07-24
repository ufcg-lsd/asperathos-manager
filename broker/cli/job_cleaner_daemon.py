import datetime
import time
import threading

from broker.service.api import v10 as v10api
from broker.service import api


def trigger_watch_thread():
    while True:
        submissions = v10api.db_connector.get_finished_jobs()
        for job_id in submissions:
            job = submissions[job_id]
            if job.thread_flag:
                now = datetime.datetime.now()
                seconds_past = (now - job.finish_time).total_seconds()
                if seconds_past > job.job_resources_lifetime:
                    job.delete_job_resources()
                    job.thread_flag = False
                    job.persist_state()

        time.sleep(api.cleaner_interval)


def start_job_cleaner():
    handling_thread = threading.Thread(target=trigger_watch_thread)
    handling_thread.daemon = True
    handling_thread.start()
