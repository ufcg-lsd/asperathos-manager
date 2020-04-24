import subprocess
from importlib import import_module
from broker.utils.logger import Log
from broker.utils.framework import monitor
from broker.utils.framework import visualizer
from broker.utils.framework import controller


API_LOG = Log("APIv10", "logs/APIv10.log")


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
    ''' Checks and replaces a submission data
    for plugin name:module binding.
    Example: If a plugin name is 'Kubejobs' but its
    import module is 'kubejobs', this replaces plugin name
    to plugin module.
    '''
    plugin_fields = [("plugin", "manager"),
                     ("visualizer_plugin", "visualizer")]

    for p, c in plugin_fields:
        plugin = submission_data.get('plugin_info').get(p)
        if not plugin:
            plugin = submission_data.get(p)
        plugin = db.get_by_name_and_component(plugin, c)
        submission_data[p] = plugin.module

    for plugin_key in submission_data.get('plugin_info').get('control_info'):
        plugin_name = submission_data.get('plugin_info').get('control_info').\
            get(plugin_key).get('plugin')
        API_LOG.log("Checking controller plugin: %s" % plugin_name)
        plugin = db.get_by_name_and_component(plugin_name, "controller")
        API_LOG.log("Changing to controller module: %s" % plugin.module)
        submission_data['plugin_info']['control_info'][plugin_key]['plugin'] = \
            plugin.module

    for plugin_key in submission_data.get('plugin_info').get('monitor_info'):
        plugin_name = submission_data.get('plugin_info').get('monitor_info').\
            get(plugin_key).get('plugin')
        API_LOG.log("Checking monitor plugin: %s" % plugin_name)
        plugin = db.get_by_name_and_component(plugin_name, "monitor")
        API_LOG.log("Changing to monitor module: %s" % plugin.module)
        submission_data['plugin_info']['monitor_info'][plugin_key]['plugin'] = \
            plugin.module
