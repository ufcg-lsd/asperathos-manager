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
import dill
import etcd3
import json

from broker.persistence.persistence_interface import PersistenceInterface
from broker.persistence.etcd_db.model import Plugin


class Etcd3JobPersistence(PersistenceInterface):

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


class Etcd3PluginPersistence(PersistenceInterface):

    PLUGIN_PREFIX = 'asperathos_plugin:'

    def __init__(self, ip, port):

        self.etcd_connection = etcd3.client(str(ip), str(port))

    def put(self, plugin_name, source, plugin_source,
            component, plugin_module=None):

        plugin_data = {
            "name": plugin_name,
            "source": source,
            "plugin_source": plugin_name,
            "component": component,
            "module": plugin_module or plugin_name
        }

        plugin = Plugin(name=plugin_name, source=source,
                        plugin_source=plugin_source,
                        component=component,
                        module=plugin_module)

        with self.etcd_connection.lock('put', ttl=5):
            self.etcd_connection.\
                put('{}{}-{}'.format(Etcd3PluginPersistence.PLUGIN_PREFIX,
                                     plugin_name, component),
                    json.dumps(plugin_data))

        return plugin

    def get(self, plugin_name):
        with self.etcd_connection.lock('get', ttl=5):
            data = self.etcd_connection.\
                get('{}{}'.format(Etcd3PluginPersistence.PLUGIN_PREFIX,
                                  plugin_name))[0]
            return data

    def get_by_name_and_component(self, plugin_name, component):
        with self.etcd_connection.lock('get', ttl=5):
            data = self.etcd_connection.\
                get('{}{}-{}'.format(Etcd3PluginPersistence.PLUGIN_PREFIX,
                                     plugin_name, component))[0]
            return data

    def delete(self, plugin_name):
        with self.etcd_connection.lock('del', ttl=5):
            self.etcd_connection.\
                delete('{}{}'.format(Etcd3PluginPersistence.PLUGIN_PREFIX,
                                     plugin_name))

    def delete_all(self):
        with self.etcd_connection.lock('delall', ttl=5):
            self.etcd_connection.\
                delete_prefix(Etcd3PluginPersistence.PLUGIN_PREFIX)

    def get_all(self, prefix=PLUGIN_PREFIX):

        with self.etcd_connection.lock('getall', ttl=5):
            raw_plugins = self.etcd_connection.get_prefix(prefix)

        plugins = []
        for p, metadata in raw_plugins:
            p = json.loads(p)
            plugins.append(Plugin(**p))
        return plugins
