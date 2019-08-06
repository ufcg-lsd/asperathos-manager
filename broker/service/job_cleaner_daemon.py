import time
import threading

from broker.utils.accumulated_sum_linked_list import AccumulatedSumLinkedList


class JobCleanerDaemon():

    def __init__(self, submissions):
        self.submissions = submissions
        self.queue = AccumulatedSumLinkedList()
        self.thread = None
        self.active = False

    def start_delete_resources_management(self):
        while not self.queue.is_empty():
            time.sleep(1)
            self.queue.head.value.remaining_time -= 1
            if self.queue.head.value.remaining_time <= 0:
                jobs_finished_ids = self.queue.pop().value.get_app_ids()
                for job_id in jobs_finished_ids:
                    job = self.submissions[job_id]
                    job.delete_job_resources()
        self.active = False

    def insert_element(self, app_id, time):
        element = JobRepr(app_id, time)
        self.queue.insert(element)
        if not self.active:
            self.active = True
            self.start_thread()

    def start_thread(self):
        self.thread = \
            threading.Thread(target=self.start_delete_resources_management)
        self.thread.daemon = True
        self.thread.start()


class JobRepr():

    def __init__(self, app_id, remaining_time):

        self.remaining_time = remaining_time
        self.app_ids = [app_id]

    def get_app_ids(self):
        return self.app_ids

    def get_remaining_time(self):
        return self.remaining_time

    def set_remaining_time(self, new_remaining_time):
        self.remaining_time = new_remaining_time

    def __repr__(self):
        return str(self.app_ids) + ": " + str(self.remaining_time) + " sec"
