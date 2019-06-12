import subprocess
from importlib import import_module

from broker.utils.framework import monitor
from broker.utils.framework import visualizer
from broker.utils.framework import controller


class PluginSources(object):
    GIT = 'git'
    PIP = 'pip'


class Components(object):
    MANAGER = 'manager'
    VISUALIZER = 'visualizer'
    CONTROLLER = 'controller'
    MONITOR = 'monitor'


def install_plugin(source, plugin):
    if source == PluginSources.GIT:
        install_name = 'git+' + plugin
    elif source == PluginSources.PIP:
        install_name = plugin
    try:
        exit_status = subprocess.check_call(['pip',
                                             'install',
                                             '--upgrade',
                                             install_name])
    except Exception:
        return False
    return exit_status == 0


def get_plugin(plugin_module):
    plugin = import_module(plugin_module).PLUGIN
    return plugin()


def install_in_visualizer(source, plugin):
    return visualizer.install_plugin(source, plugin)


def install_in_monitor(source, plugin):
    return monitor.install_plugin(source, plugin)


def install_in_controller(source, plugin):
    return controller.install_plugin(source, plugin)
