# IWS-Demo API

## Field types

In addition to the generic JSON field formats, the following field types used in this API have additional attributes and constraints:

Type | Constraints
---- | -----------
`<priority>` | Integer in range 1-32766 or `null`
`<uuidstring>` | UUID version 4 in string form, with or without hyphens
`<urlstring>` | URL-formatted string
`<datetime>` | UTC date/time string in the forms `yyyy-mm-dd` or `yy-mm-ddThh:mm:ss`, or `null`
`<prodarea>` | One of the following strings: "Policies", "Billing", "Claims", "Reports"
`<status>` | One of the following strings: "Complete", "Rejected", "Deferred"

## Object formats

Client `<client>`:
```
{
  "id": <uuidstring>,			# Client ID
  "name": <string>,				# Client name
  "con_name": <string>,			# Contact name
  "con_mail": <string>,			# Contact email
  "date_add": <datetime>,		# Date added
  "open_count": <integer>,		# Number of open requests (RELATIONAL)
  "open_list": [ <open> ],		# List of open requests (RELATIONAL)
  "closed_count": <integer>,	# Number of closed requests (RELATIONAL)
  "closed_list": [ <closed> ]	# List of closed requests (RELATIONAL)
}
```

Feature request `<req>`:
```
{
  "id": <uuidstring>,			# Request ID
  "title": <string>,			# Request title (128 chars max)
  "desc": <string>,				# Request description
  "ref_url": <urlstring>,		# Reference URL (254 chars max)
  "prod_area": <prodarea>,		# Product area
  "date_cr": <datetime>,		# Date created
  "user_cr": <string>,			# Username created
  "date_up": <datetime>,		# Date last updated
  "user_up": <string>,			# Username last updated
  "open_list": [ <open> ],		# List of open requests (RELATIONAL)
  "closed_list": [ <closed> ]	# List of closed requests (RELATIONAL)
}
```

Open request `<open>`:
```
{
  "client_id": <uuidstring>,	# Client ID (RELATIONAL)
  "priority": <priority>,		# Client priority
  "date_tgt": <datetime>,		# Target completion date
  "opened_at": <datetime>,		# Date opened
  "opened_by": <string>,		# Username opened
  "req": <req>					# Request details (RELATIONAL)
}
```

Closed request `<closed>`:
```
{
  "client_id": <uuidstring>,,	# Client ID (RELATIONAL)
  "priority": <priority>,		# Client priority
  "date_tgt": <datetime>,		# Target completion date
  "opened_at": <datetime>,		# Date opened
  "opened_by": <string>,		# Username opened
  "closed_at": <datetime>,		# Date closed
  "closed_by": <string>,		# Username closed
  "status": <status>,			# Closed status
  "reason": <string>,			# Reason for closing
  "req": <req>					# Request details (RELATIONAL)
}
```

## API notes

### Default fields

Most endpoints return a subset of object fields by default. These will be noted in the return values.

Individual fields of an object will be noted as follows:
```
<type field>
```

Relational fields, as noted in their respective object format descriptions above, will only be included when explicitly included in return value listings. Object types abbreviated simply as `<type>` will include all non-relational fields of that object type.

### Query string parameters

All endpoints which return `<req>` objects, either at the reponse's top level or within another object, can specify which fields are returned using the `fields` query string parameter. This can be included multiple times, or as a combined parameter with the values separated by commas. Using the value `all` will return all fields excluding relational references (ie a `<req>` object inside an `<open>` object will not include the fields `open_list` or `closed_list`).

Example using multiple values:
```
?fields=id&fields=title&fields=date_cr
```

Example using combined values:
```
?fields=id,title,date_cr
```

Example for all fields:
```
?fields=all
```

## API endpoints

#### `/featreq/auth`

Methods: GET, POST

**GET**

Show current authentication details.

Return value, status code 200:
```
{
 "logged_in": <boolean>,
 "username": <string>,        # Current username, empty if not logged in
 "full_name": <string>,       # Full name of user, [anonymous] if not logged in
 "csrf_token": <string>,      # CSRF token string matching cookie "csrftoken"
 "session_expiry": <integer>  # Time until session expires, in seconds
}
```

**POST**

Log in:
```
{
 "action": "login",
 "username": <string>,        # Required
 "password": <string>,        # Required
}
```

Return value, status code 200:
*As per GET*

Log out:
```
{
 "action": "logout",
 "username": <string>,        # Required
}
```

Return value, status code 200:
*As per GET*


#### `/featreq/client/`

Methods: GET, POST

**GET**

List of clients available.

Return value, status code 200:
```
{
 "client_count": <integer>,
 "client_list": [
  {
   "id": <client id>,
   "name": <client name>,
   "open_count": <client open_count>,
   "closed_count": <client closed_count>
  }
 ]
}
```

**POST**

Create new client:
```
{
 "action": "create",	# Required
 "name": <string>,		# Required
 "con_name": <string>,
 "con_mail": <string>
}
```

Return value, status code 201:
```
{
 "client": <client>
}
```


#### `/featreq/client/<client id>`

Methods: GET, POST

**GET**

Client details for given id.

Return value, status code 200:
```
{
 "client": <client>
}
```

**POST**

Update client:
```
{
 "action": "update",	# Required
 "name": <string>,
 "con_name": <string>,
 "con_mail": <string>
}
```

Return value, status code 200:
*As per GET*

#### `/featreq/client/<client id>/open/`

Methods: GET, POST

**GET**

List of open requests for given client id.

Return value, status code 200:
```
{
 "client": {
  "id": <client id>,
  "open_list": [
   {
    "priority": <open priority>,
    "date_tgt": <open date_tgt>,
    "opened_at": <open opened_at>,
    "opened_by": <open opened_by>,
    "req": {
     "id": <req id>
    }
   }
  ]
 }
}
```

**POST**

Open a request:
```
{
 "action": "open",			# Required
 "req_id": <uuidstring>,	# Required
 "priority": <priority>,
 "date_tgt": <datetime>
}
```

Return value, status code 200:
*As per GET*

Update an open request:
```
{
 "action": "update",		# Required
 "req_id": <uuidstring>,	# Required
 "priority": <priority>,
 "date_tgt": <datetime>
}
```

Return value, status code 200:
*As per GET*

Close an open request:
```
{
 "action": "close",			# Required
 "req_id": <uuidstring>,	# Required
 "status": <status>,		# Default "Complete"
 "reason": <string>			# Default "Request completed"
}
```

Return value, status code 200:
*As per GET*


#### `/featreq/client/<client id>/closed/`

Methods: GET

**GET**

List of closed requests for given client id.

Return value, status code 200:
```
{
 "client": {
  "id": <client id>,
  "closed_list": [
   {
    "priority": <closed priority>,
    "date_tgt": <closed date_tgt>,
    "opened_at": <closed opened_at>,
    "opened_by": <closed opened_by>,
    "closed_at": <closed closed_at>,
    "closed_by": <closed closed_by>,
    "status": <closed status>,
    "reason": <closed reason>,
    "req": {
     "id": <req id>
    }
   }
  ]
 }
}
```

#### `/featreq/client/<client id>/all/`

Methods: GET

**GET**

List of open and closed requests for given client id.

Return value, status code 200:
```
{
 "client": {
  "id": <client id>,
  "open_list": [
   {
    "priority": <open priority>,
    "date_tgt": <open date_tgt>,
    "opened_at": <open opened_at>,
    "opened_by": <open opened_by>,
    "req": {
     "id": <req id>
    }
   }
  ]
  "closed_list": [
   {
    "priority": <closed priority>,
    "date_tgt": <closed date_tgt>,
    "opened_at": <closed opened_at>,
    "opened_by": <closed opened_by>,
    "closed_at": <closed closed_at>,
    "closed_by": <closed closed_by>,
    "status": <closed status>,
    "reason": <closed reason>,
    "req": {
     "id": <req id>
    }
   }
  ]
 }
}
```


#### `/featreq/req/`

List of requests available.

Methods: GET, POST

**GET**

Return value, status code 200:
```
{
 "req_count": <integer>,
 "req_list": [
  {
   "id": <req id>,
   "title": <req title>
  }
 ]
}
```

**POST**

Create new request:
```
{
 "action": "create",		# Required
 "id": <uuidstring>,
 "title": <string>,			# Required
 "desc": <string>,			# Required
 "ref_url": <urlstring>,
 "prod_area": <prodarea>,	# Default "Policies"
}
```

Return value, status code 201:
```
{
 "req": <req>
}
```


#### `/featreq/req/open/`

List of open requests.

Methods: GET

**GET**

Return value, status code 200:
```
{
 "req_count": <integer>,
 "req_list": [
  {
   "id": <req id>,
   "title": <req title>
   "open_list": [
    {
     "client_id": <client id>,
     "priority": <open priority>,
     "date_tgt": <open date_tgt>,
     "opened_at": <open opened_at>,
     "opened_by": <open opened_by>,
    }
   ]
  }
 ]
}
```


#### `/featreq/req/closed/`

List of closed requests.

Methods: GET

**GET**

Return value, status code 200:
```
{
 "req_count": <integer>,
 "req_list": [
  {
   "id": <req id>,
   "title": <req title>
   "closed_list": [
    {
     "client_id": <client id>,
     "priority": <closed priority>,
     "date_tgt": <closed date_tgt>,
     "opened_at": <closed opened_at>,
     "opened_by": <closed opened_by>,
     "closed_at": <closed closed_at>,
     "closed_by": <closed closed_by>,
     "status": <closed status>,
     "reason": <closed reason>
    }
   ]
  }
 ]
}
```


#### `/featreq/req/<req id>`

Request details for given id.

Methods: GET, POST

**GET**

Return value, status code 200:
```
{
 "req": <req>
}
```

**POST**

Update request:
```
{
 "action": "update",		# Required
 "title": <string>,
 "desc": <string>,
 "ref_url": <urlstring>,
 "prod_area": <prodarea>
}

```

Return value, status code 200:
*As per GET*


#### `/featreq/req/<req id>/open/`

Methods: GET

**GET**

List of open requests for given request id.

Return value, status code 200:
```
{
 "req": {
  "id": <req id>,
  "open_list": [
   {
   	"client_id": <client id>,
    "priority": <open priority>,
    "date_tgt": <open date_tgt>,
    "opened_at": <open opened_at>,
    "opened_by": <open opened_by>,
   }
  ]
 }
}
```


#### `/featreq/req/<req id>/closed/`

Methods: GET

**GET**

List of closed requests for given request id.

Return value, status code 200:
```
{
 "req": {
  "id": <req id>,
  "closed_list": [
   {
   	"client_id": <client id>,
    "priority": <closed priority>,
    "date_tgt": <closed date_tgt>,
    "opened_at": <closed opened_at>,
    "opened_by": <closed opened_by>,
    "closed_at": <closed closed_at>,
    "closed_by": <closed closed_by>,
    "status": <closed status>,
    "reason": <closed reason>,
   }
  ]
 }
}
```


#### `/featreq/req/<req id>/all/`

Methods: GET, POST

**GET**

List of open and closed requests for given request id.

Return value, status code 200:
```
{
 "req": {
  "id": <req id>,
  "open_list": [
   {
   	"client_id": <client id>,
    "priority": <open priority>,
    "date_tgt": <open date_tgt>,
    "opened_at": <open opened_at>,
    "opened_by": <open opened_by>,
   }
  ]
  "closed_list": [
   {
   	"client_id": <client id>,
    "priority": <closed priority>,
    "date_tgt": <closed date_tgt>,
    "opened_at": <closed opened_at>,
    "opened_by": <closed opened_by>,
    "closed_at": <closed closed_at>,
    "closed_by": <closed closed_by>,
    "status": <closed status>,
    "reason": <closed reason>,
   }
  ]
 }
}
```

**POST**

Open a request:
```
{
 "action": "open",			# Required
 "client_id": <uuidstring>,	# Required
 "priority": <priority>,
 "date_tgt": <datetime>
}
```

Return value, status code 200:
*As per GET*

Close an open request:
```
{
 "action": "close",			# Required
 "client_id": <uuidstring>,	# If omitted, will close for all clients
 "status": <status>,		# Default "Complete"
 "reason": <string>			# Default "Request completed"
}
```

Return value, status code 200:
*As per GET*



