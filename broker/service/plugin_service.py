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


def check_submission(db, submission_data):
    ''' Replaces the name of the plugin for a dict
    with plugin information
    '''
    plugin_fields = [("plugin", "manager"),
                     ("control_plugin", "controller"),
                     ("monitor_plugin", "monitor"),
                     ("visualizer_plugin", "visualizer")]

    for p, c in plugin_fields:
        is_manager = False
        plugin = submission_data.get('plugin_info').get(p)
        if not plugin:
            is_manager = True
            plugin = submission_data.get(p)
        plugin = db.get_by_name_and_component(plugin, c)
        if not is_manager:
            submission_data['plugin_info'][p] = plugin.to_dict()
        else:
            submission_data[p] = plugin.to_dict()
