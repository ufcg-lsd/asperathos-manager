# KubeJobs Plugin

## How does it works?

The following steps describes the basic flow of an execution using KubeJobs:

* Step 1: The client sends a POST request to the Asperathos Manager with a JSON body describing the execution.
* Step 2: The Manager creates a Redis service in the cluster, enqueues the items described in the input file in Redis through the queue auxiliary service.
* Step 3: The application execution is triggered on the cluster.
* Step 4: The application running on Kubernetes cluster starts to consume items from the Redis storage.
* Step 5: The Monitor is triggered by the Manager when application starts to run.
* Step 6: The Monitor periodically gets the number of processed items from the queued service.
* Step 7: As soon as metrics are being published, the Manager starts the Controller, which consumes metrics from Redis to take decisions about scaling based on the predefined control logic.


## Configuration

In order to correctly configure the Manager to execute the KubeJobs plugin, modifications in the *broker.cfg* file are necessary. Following you can check an example of a configuration file that can be used to execute the KubeJobs plugin.

### Configuration file example:

```
[general]
host = 0.0.0.0
port = 1500
plugins = kubejobs

[services]
controller_url = http://0.0.0.0:5000
monitor_url = http://0.0.0.0:5001
visualizer_url = http://0.0.0.0:5002
optimizer_url = http://0.0.0.0:5003
authorization_url = http://0.0.0.0:5004

[kubejobs]
# The path for the configuration file of the Kubernetes cluster that will be used
k8s_conf_path = 
# IP of the one of the nodes contained in the Kubernetes clusters that will be used
redis_ip = 
# Count queue ip. Can be the ip of one of the nodes contained in the Kubernetes clusters that will be used
count_queue =
```

## Execute plugin

In order to execute the plugin, a JSON needs to be correctly configurate with all necessary variables that will be used by Asperathos components. Following you can check an example of this JSON file that will be used to sends a POST request to the Asperathos Manager.

### JSON file example:

```javascript
{  
   "plugin":"kubejobs",
   "plugin_info":{  
      "username":"usr",
      "password":"psswrd",
      "cmd":[  
         [...]
      ],
      "img":"img",
      "init_size":1,
      "redis_workload":"workload",
      "config_id":"id",
      "control_plugin":"kubejobs",
      "control_parameters":{  
         [...]
      },
      "monitor_plugin":"kubejobs",
      "monitor_info":{  
         [...]
      },
      "enable_visualizer":true,
      "visualizer_plugin":"k8s-grafana",
      "visualizer_info":{  
         [...]
      },
      "env_vars":{  
         [...]
      }
   }
}
```