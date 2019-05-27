# Copyright (c) 2019 UFCG-LSD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from broker.persistence.persistence_interface import PersistenceInterface
from broker.persistence.sqlite.model import JobState

import dill
import peewee


class SqlitePersistence(PersistenceInterface):

    def __init__(self):
        try:
            JobState.create_table()
        except peewee.OperationalError:
            pass

    def put(self, app_id, state):

        new_state = JobState(app_id=app_id,
                             obj_serialized=dill.dumps(state))
        try:
            new_state.save()

        except peewee.IntegrityError:
            JobState.update({JobState.
                             obj_serialized: dill.dumps(state)}).\
                            where(JobState.app_id == app_id)

    def get(self, app_id):

        state = JobState.get(JobState.app_id == app_id)
        return dill.loads(state.obj_serialized)

    def delete(self, app_id):

        state = JobState.get(JobState.app_id == app_id)
        state.delete_instance()

    def delete_all(self):

        JobState.delete()

    def get_all(self):

        all_states = JobState.select()

        all_jobs = dict([(obj.app_id, dill.loads(obj.obj_serialized))
                         for obj in all_states])

        for key in all_jobs:
            current_job = all_jobs.get(key)
            current_job.synchronize()
            self.put(current_job.app_id, current_job)

        return all_jobs
