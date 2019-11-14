#  REST API Endpoints
This section provides a detailed list of avaliable endpoints in Broker REST API.

## Submit and run
  Run a submission and returns json data with id of submission.

* **URL**: `/submissions`
* **Method:** `POST`

* **JSON Request:**
	* ```javascript
	  {
	     username : [string],
	     password : [string],
	     plugin: [string],
	     plugin_info : {
	         ...
	     }
	  }
	  ```
* **Success Response:**
  * **Code:** `202` <br /> **Content:** 
	  * ```javascript
	    {
	       job_id : [string]
	    }
		```
		
* **Error Response:**
  * **Code:** `400 BAD REQUEST` and `401 UNAUTHORIZED`<br />


## Stop submission
  Stop a running submission.

* **URL**: `/submissions/:id/stop`
* **Method:** `PUT`

* **JSON Request:**
	* ```javascript
	  {
	     username : [string],
	     password : [string]
	  }
	  ```
* **Success Response:**
  * **Code:** `204` <br />
		
* **Error Response:**
  * **Code:** `400 BAD REQUEST` and `401 UNAUTHORIZED`<br />

## Delete submission
  Delete a done submission.

* **URL**: `/submissions/:id`
* **Method:** `DELETE`

* **JSON Request:**
	* ```javascript
	  {
	     username : [string],
	     password : [string]
	  }
	  ```
* **Success Response:**
  * **Code:** `204` <br />
		
* **Error Response:**
  * **Code:** `400 BAD REQUEST` and `401 UNAUTHORIZED`<br />

## Delete all submissions
  Delete all done submissions.

* **URL**: `/submissions`
* **Method:** `DELETE`

* **JSON Request:**
	* ```javascript
	  {
	     username : [string],
	     password : [string]
	  }
	  ```
* **Success Response:**
  * **Code:** `204` <br />
		
* **Error Response:**
  * **Code:** `400 BAD REQUEST` and `401 UNAUTHORIZED`<br />

## List submissions
  List all submissions.

* **URL**: `/submissions`
* **Method:** `GET`
* **Success Response:**
  * **Code:** `200` <br /> **Content:** 
	  * ```javascript
	    {
	       submission1 : {
	          status: [string]
	       },
     	   [...],
	       submissionN : {
	          status: [string]
	       }		 
	    }
		```

## Submission status
  Returns json data with detailed status of submission.

* **URL**: `/submissions/:id`
* **Method:** `GET`
* **Success Response:**
  * **Code:** `200` <br /> **Content:** 

	**Before job finish**
	  * ```javascript
	    {	
		   app_id: [string]
	       status : [string],
	       execution_time : [string],
	       starting_time : [string],
		   visualizer_url: [string],
		   redis_ip: [string],
		   redis_port: [string]
	    }
	   	```
	**After job finish**
	  * ```javascript	
		{	
		   app_id: [string]
	       status : [string],
	       execution_time : [string],
	       starting_time : [string],
		   visualizer_url: [string],
		   redis_ip: [string],
		   redis_port: [string],
		   execution_time: [int],
		   scaling_strategy: [string],
		   heuristic_options: [string],
		   min_error: [float],
		   max_error: [float],
		   final_replicas: [int],
		   final_error: [float]
	    }

		```
	
* **Error Response:**
  * **Code:** `400 BAD REQUEST` <br />

## Submission log
  Returns json data with log of submission.

* **URL**: `/submissions/:id/log`
* **Method:** `GET`
* **Success Response:**
  * **Code:** `200` <br /> **Content:** 
	  * ```javascript
	    {
	       execution : [string],
  	       stderr : [string],
  	       stdout : [string]
	    }
		```
		
* **Error Response:**
  * **Code:** `400 BAD REQUEST` <br />

## Get Visualizer url
  Return the visualizer URL of a specific submission.

* **URL**: `/submissions/:app_id/visualizer`
* **Method:** `GET`
* **Success Response:**
  * **Code:** `200` <br /> **Content:** 
	  * ```javascript
	    {
			visualizer_url: [string]
		}
		```
		
* **Error Response:**
  * **Code:** `400 BAD REQUEST` <br />

## Add cluster
  Add a new cluster reference into the Asperathos section

* **URL**: `/submissions/cluster`
* **Method:** `POST`
* **JSON Request:**
	* ```javascript
		{
			"user" : [string],
			"password" : [string],
			"cluster_name" : [string],
			"cluster_config" : [string]
		}
* **Success Response:**
  * **Code:** `220` <br /> **Content:** 
	  * ```javascript
	    {
			"cluster_name" : [string],
			"status": [string],
			"reason": [string]
	    }
		```

## Add certificate
  Add a certificate in the a cluster reference into the Asperathos section

* **URL**: `/submissions/cluster/:cluster_name/certificate`
* **Method:** `POST`
* **JSON Request:**
	* ```javascript
		{
			"user" : [string],
			"password" : [string],
			"certificate_name" : [string],
			"certificate_content" : [string]
		}
* **Success Response:**
  * **Code:** `220` <br /> **Content:** 
	  * ```javascript
	    {
			"cluster_name" : [string],
			"certificate_name" : [string],
			"status": [string],
			"reason": [string]
	    }
		```

## Delete cluster
  Delete a cluster reference of the Asperathos section

* **URL**: `/submissions/cluster/:cluster_name`
* **Method:** `DELETE`
* **JSON Request:**
	* ```javascript
		{
			"user" : [string],
			"password" : [string]
		}
* **Success Response:**
  * **Code:** `220` <br /> **Content:** 
	  * ```javascript
	    {
			"cluster_name" : [string],
			"status": [string],
			"reason": [string]
	    }
		```

## Delete certificate
  Delete a certificate of a cluster reference in the Asperathos section

* **URL**: `/submissions/cluster/:cluster_name/certificate/:certificate_name`
* **Method:** `DELETE`
* **JSON Request:**
	* ```javascript
		{
			"user" : [string],
			"password" : [string]
		}
* **Success Response:**
  * **Code:** `220` <br /> **Content:** 
	  * ```javascript
	    {
			"cluster_name" : [string],
			"certificate_name" : [string],
			"status": [string],
			"reason": [string]
	    }
		```

## Activate cluster
  Start to use the informed cluster as active cluster in the Asperathos section.

* **URL**: `/submissions/cluster/:cluster_name/activate`
* **Method:** `PUT`
* **JSON Request:**
	* ```javascript
		{
			"user" : [string],
			"password" : [string]
		}

## Get clusters
  List all clusters added in a Asperathos instance.

* **URL**: `/submissions/cluster`
* **Method:** `GET`
* **Success Response:**
  * **Code:** `200` <br /> **Content:** 
	  * ```javascript
	    {
    		"cluster1": {
        	"active": false,
        	"conf_content": "cluster1-content"
    		},
    		"cluster2": {
        	"certificate1": "cert1-content",
					"certificate2": "cert2-content",
					"certificateN": "certN-content",
        	"active": true,
        	"conf_content": "cluster2-content"
    		},
				[...]
				,
    		"clusterN": {
        	"active": false,
        	"conf_content": "clusterN-content"
    		}
			}
		```

## Get activated cluster
  Get the current activated cluster in a Asperathos instance.

* **URL**: `/submissions/cluster/activate`
* **Method:** `GET`
* **Success Response:**
  * **Code:** `200` <br /> **Content:** 
	  * ```javascript
	    {
    		"cluster-activated": {
        	"active": true,
        	"conf_content": "cluster-content",
					"certificate": "certificate-content"
    		}
			}
		```
## Install a plugin
  Install or update a plugin 

* **URL**: `/plugins`
* **Method:** `POST`
* **JSON Request:**
	* ```javascript
        {
            "plugin_name": [string],
            "plugin_source": [string],
            "install_source": [string],
            "plugin_module": [string],
            "component": [string]
        }
* **Success Response:**
  * **Code:** `200` <br /> **Content:** 
	  * ```javascript
	    {
			"message": [string]
	    }
		```
* **Error Response:**
  * **Code:** `400 BAD REQUEST`
