# Copyright (c) 2017 UFCG-LSD.
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

import abc

import six
from stevedore import enabled

from broker import exceptions as ex
from broker.service import api
from broker.utils.logger import Log


LOG = Log("Servicev10", "logs/serviceAPIv10.log")


def required(fun):
    return abc.abstractmethod(fun)


def required_with_default(fun):
    return fun


def optional(fun):
    fun.__not_implemented__ = True
    return fun


@six.add_metaclass(abc.ABCMeta)
class PluginInterface(object):

    name = 'plugin_interface'

    @required
    def get_title(self):
        """Plugin title

        For example:

            "Generic Provisioning"
        """
        pass

    @required_with_default
    def get_description(self):
        """Optional description of the plugin

        """
        pass

    def to_dict(self):
        return {
            'name': self.name,
            'title': self.get_title(),
            'description': self.get_description(),
        }

    @required
    def execute(self, data):
        """Method that executes creation and job runs

        """
        pass


class PluginManager(object):
    def __init__(self):
        self.plugins = {}
        self._load_plugins()

    def _load_plugins(self):
        config_plugins = api.plugins
        extension_manager = enabled.EnabledExtensionManager(
            check_func=lambda ext: ext.name in config_plugins,
            namespace='broker.execution.plugins',
            invoke_on_load=True
        )

        for ext in extension_manager.extensions:
            if ext.name in self.plugins:
                raise ex.ConfigurationError(
                    ("Plugin with name '%s' already exists.") % ext.name)
            ext.obj.name = ext.name
            self.plugins[ext.name] = ext.obj
            LOG.log("Plugin {plugin_name} loaded {entry_point}".format(
                    plugin_name=ext.name,
                    entry_point=ext.entry_point_target))

        if len(self.plugins) < len(config_plugins):
            loaded_plugins = set(six.iterkeys(self.plugins))
            requested_plugins = set(config_plugins)
            raise ex.ConfigurationError(
                ("Plugins couldn't be loaded: %s") %
                ", ".join(requested_plugins - loaded_plugins))

    def get_plugins(self):
        return [self.get_plugin(name) for name in api.plugins]

    def get_plugin(self, plugin_name):
        return self.plugins.get(plugin_name)


PLUGINS = None


def setup_plugins():
    global PLUGINS
    PLUGINS = PluginManager()


@six.add_metaclass(abc.ABCMeta)
class ApplicationExecutor(object):

    @required
    def get_application_state(self):
        pass

    @required
    def terminate_job(self):
        pass

    @required
    def update_application_state(self, state):
        pass

    @required
    def get_application_execution_time(self):
        pass

    @required
    def get_application_start_time(self):
        pass


class GenericApplicationExecutor(ApplicationExecutor):

    def __init__(self):
        pass

    def get_application_state(self):
        pass

    def terminate_job(self):
        pass

    def update_application_state(self, state):
        pass

    def stop_application(self, redis):
        pass

    def get_application_execution_time(self):
        pass

    def get_application_start_time(self):
        pass
