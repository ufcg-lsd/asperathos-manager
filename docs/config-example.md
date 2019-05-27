# Config example

## broker.cfg: 
```
[services]
controller_url = <Ex: 0.0.0.0:5000>
monitor_url =  <Ex: 0.0.0.0:5001>
visualizer_url = <Ex: 0.0.0.0:5002>
optimizer_url =
authorization_url =

[general]
port = <Ex: 1500>
plugins = <Ex: plugin1,plugin2,plugin3>

[persistence]
plugin_name = <Optional. "sqlite" is default when this field is blank>
persistence_ip = <Optional. It's needed when the persistence is remote, like etcd. Ex: 0.0.0.0>
persistence_port = <Optional. It's needed when the persistence is remote, like etcd. Ex: 1675>
local_database_path = <Path to sqlite.bd file. Ex: ./local_database/sqlite.db. The file ".db" is created if not exists.>

[kubejobs]
k8s_conf_path = <Optional. Path to kuberntes config file. If blank, the default path is ./data/conf>
redis_ip = <Optional. Gets the Ip of any node in the cluster if not specified. Ex: 0.0.0.0>

[plugin1]
p1_info1 = 
p1_info2 =
p1_info3 = 

[plugin2]
p2_info1 =
p2_info2 =

[plugin3]
p3_info1 =
p3_info2 =
p3_info3 =
p3_info4 =
```
