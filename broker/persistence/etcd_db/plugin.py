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

import dill
import etcd3


class Etcd3Persistence(PersistenceInterface):

    def __init__(self, ip, port):

        self.etcd_connection = etcd3.client(str(ip), str(port))

    def put(self, app_id, state):
        with self.etcd_connection.lock('put', ttl=5):
            ser = dill.dumps(state)
            self.etcd_connection.put(str(app_id), ser)

    def get(self, app_id):
        with self.etcd_connection.lock('get', ttl=5):
            data = self.etcd_connection.get(str(app_id))[0]
            return dill.loads(data)

    def delete(self, app_id):
        with self.etcd_connection.lock('del', ttl=5):
            self.etcd_connection.delete(str(app_id))

    def delete_all(self, prefix='kj-'):
        with self.etcd_connection.lock('delall', ttl=5):
            self.etcd_connection.delete_prefix(prefix)

    def get_all(self, prefix="kj-"):

        with self.etcd_connection.lock('getall', ttl=5):
            all_jobs = dict([(m.key, dill.loads(n)) for (n, m)
                             in self.etcd_connection.get_prefix(prefix)])

            for key in all_jobs:
                current_job = all_jobs.get(key)
                current_job.synchronize()
                self.put(current_job.app_id, current_job)

        return all_jobs
