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
	       id : [string]
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


## Terminate submission
  Terminate a running submission.

* **URL**: `/submissions/:id/terminate`
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
     	       ...
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
	  * ```javascript
	    {
	       status : [string],
	       execution_time : [string],
	       start_time : [string]
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
