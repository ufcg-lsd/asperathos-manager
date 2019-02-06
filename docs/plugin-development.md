# Plugin development
This is an important step to enjoy all flexibility and features that this framework provides.

## Steps

1. In the *broker.cfg* file add the plugin to the list of desired plugins:

### Example:

```
[general]
plugins = plugin1,plugin2,my_new_plugin

[my_new_plugin]
var1 = 
var2 = 
var3 = 
```

In this tutorial, we will use MyNewPlugin as the plugin name

2. Create a new if statement condition in the file *broker/service/api/__init__.py* that will recognize if the new plugin added is informed in the configuration file (*broker.cfg*). If this condition is true, then the necessary variables to execute the plugin needs to be informed in the *broker.cfg* file and computed in the *broker/service/api/__init__.py*.

### Example:

```
import ConfigParser

try:

[...]

if 'my_new_plugin' in plugins:
    var1 = config.get('my_new_plugin', 'var1')
    var2 = config.get('my_new_plugin', 'var2')
    var3 = config.get('my_new_plugin', 'var3')

[...]
```

3. Create a new folder under *broker/plugins* with the desired plugin name and add *__init__.py*.
 
4. Write a new python class under *broker/plugins/mynewplugin*
 
It must implement the methods *get_title*, *get_description*, *to_dict* and *execute*.
 
- **get_title(self)**
  - Returns plugin title
 
- **get_description(self)**
  - Returns plugin description
 
- **to_dict(self)**
  - Return a dict with the plugin information, name, title and description
 
- **execute(self, data)**
  - Actually execute the logic of cluster creation and job execution
  - Returns information if the execution was successful or not
    
### Example:

```
from broker.plugins import base

class MyNewPluginProvider(base.PluginInterface):

    def get_title(self):
        return 'My New Plugin'

    def get_description(self):
        return 'My New Plugin'

    def to_dict(self):
        return {
            'name': self.name,
            'title': self.get_title(),
            'description': self.get_description(),
        }

    def execute(self, data):
        return True
```

5. Add the new plugin to *setup.py* under entry_points:

```
    entry_points={
        'console_scripts': [
            'broker=broker.cli.main:main',
        ],
        'broker.execution.plugins': [
            'my_new_plugin=broker.plugins.my_new_plugin.plugin:MyNewPluginProvider',
        ],
```
 
Note: Make sure that the name matches under *setup.py* and the *broker.cfg* otherwise the plugin won’t be loaded.
