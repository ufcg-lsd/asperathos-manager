BASIC_PLUGINS = [
        {
            "name": "kubejobs",
            "source": "",
            "component": "manager",
            "plugin_source": "",
            "module": "kubejobs"
        },
        {
            "name": "kubejobs",
            "source": "",
            "component": "controller",
            "plugin_source": "",
            "module": "kubejobs"
        },
        {
            "name": "kubejobs",
            "source": "",
            "component": "monitor",
            "plugin_source": "",
            "module": "kubejobs"
        },
        {
            "name": "k8s-grafana",
            "source": "",
            "component": "visualizer",
            "plugin_source": "",
            "module": "k8s-grafana"
        },
    ]


def check_basic_plugins(db):
    ''' This function checks if the
    basic plugins (kubejobs) are registered into
    the database.
    '''

    installed_plugins = db.get_all()

    for basic in BASIC_PLUGINS:
        name = basic.get('name')
        source = basic.get('source')
        component = basic.get('component')
        plugin_source = basic.get('plugin_source')
        module = basic.get('module')
        is_installed = False
        for installed in installed_plugins:
            if installed.name == name and \
               installed.component == component:

                is_installed = True
        if not is_installed:
            db.put(plugin_name=name, source=source,
                   plugin_source=plugin_source,
                   component=component,
                   plugin_module=module)
