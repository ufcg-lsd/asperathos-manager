class Plugin(object):

    def __init__(self, name, source, plugin_source,
                 component, module=None):

        self.name = name
        self.source = source
        self.plugin_source = plugin_source
        self.component = component
        self.module = module or name

    def to_dict(self):
        return {
            "name": self.name,
            "source": self.source,
            "plugin_source": self.plugin_source,
            "module": self.module,
            "component": self.component
        }
