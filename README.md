## IWS-Demo

This is a demonstration web application for creating and managing feature requests for a group of clients, written in Python using Django, and implementing a RESTful JSON API backend.

Please note that this is a work in progress, and the API is not considered stable at this time. A demonstration frontend is in consideration.

### API

Please refer to `API.md` for API endpoint documentation.

### Requirements

IWS-Demo requires Python 3.4.1 (or higher) and Django 1.9 (or higher), with bcrypt and pytz Python packages recommended. Supported deployment is through uWSGI and nginx; configuration examples for both are included.

With many platforms still using Python 2.7 as the default interpreter, and as Django will use the interpreter specified in the environment, it is *highly* recommended to use a virtualenv configured with Python 3.4.1 (or higher) when installing Django.

Without additional configuration (not detailed here), uWSGI must be installed system-wide, either using `pip` or the system package manager. A configuration helper for uWSGI to point to the virtualenv in use is included in `setup.py`.

### Installation

The following installation steps assume a Linux environment using Bash or Zsh, and with git, Python 3, and virtualenv already installed, either from source or through the distribution's package manager. Some modifications may be required for OSX or *BSD. Windows installation is not supported at this time.

All steps can be performed without root privileges, provided the user has adequate permissions for the installation paths. If installing to system locations, perform these steps as the root user or with `sudo`. If running IWS-Demo as a non-root user (highly recommended), said user must have write permissions for the IWS-Demo installation path.

#### Virtualenv setup

Initialize the virtualenv:
```
virtualenv --python=python3 /path/to/venv
```

Enter the virtualenv:
```
cd /path/to/venv
source bin/activate
```

Install Django and optional packages:
```
pip install django bcrypt pytz
```
**Note:** bcrypt and pytz require gcc to be available, and bcrypt additionally requires libffi headers to be present. Please install these dependencies via your package manager.

#### IWS-Demo setup

The following steps assume the virtualenv is active, if used, or that the default Python interpreter is 3.4+.

Clone IWS-Demo source and enter application directory:
```
git clone https://github.com/rneilson/iws-demo.git /path/to/iws-demo
cd /path/to/iws-demo/iws
```

Run setup:
```
./setup.py
```

If using uWSGI, a default .ini file will be created with the `-u` or `--uwsgi-config` options:
```
./setup.py -u
```

The setup script will run, initializing the database, creating the default `iws-admin` superuser, and writing site-specific files required by the default IWS-Demo configuration. If the `-u` option was specified, a uWSGI .ini file will be created at `/path/to/iws-demo/iws_uwsgi.ini`, including the virtualenv path detected or specified during setup. 

### Usage

As IWS-Demo is compatible with any webserver configuration supporting Django, and heavily dependent on site-specific settings, a comprehensive guide is not available here. 

#### uWSGI

When using uWSGI, the provided .ini file may be further customized as desired, and can be used to launch uWSGI with:
```
uwsgi --ini /path/to/iws-demo/iws_uwsgi.ini
```

Using the default configuration, uWSGI uses a UNIX socket at `/path/to/iws-demo/iws_uwsgi.sock` for communication with the webserver.

#### Nginx

A sample Nginx configuration is provided under the `uwsgi/` directory, including `iws_nginx.conf` and Django-compatible `uwsgi_params`. Please consult the Nginx documentation for further details.

### Additional considerations

#### Authentication

IWS-Demo uses Django's session middleware for authentication, which is cookie-based. Cookies must be enabled in the client for proper operation.

If using `curl`, this behavior can be enabled using the following command-line options:
```
curl -b /path/to/cookiejar -c /path/to/cookiejar <url>
```

The authentication endpoint is available at `/featreq/auth/`

#### Cross-site request forgery

IWS-Demo enables Django's CSRF protection by default for POST requests. Cookies must be enabled in the client for proper operation. In addition, all POST requests to API endpoints must include the `X-CSRFToken:` header with a CSRF token matching the value stored in the `csrftoken` cookie. This cookie is set by default to HTTP access only, but is explicitly available to clients at the `/featreq/auth/` API endpoint in the `csrf_token` field.

If using `curl`, this behavior can be enabled using the following command-line options:
```
curl -H 'X-CSRFToken: <csrf_token value>' <url>
```

Please note that the CSRF token will change after login; the new value is included in the response from the `/featreq/auth/` endpoint on successful authentication.

#### HTTPS additional requirements

The use of HTTPS site-wide is *strongly* recommended for externally-available IWS-Demo installations to prevent credential leakage in various forms. However, please note that Django's CSRF middleware implements strict host checking of the `Referer:` header to prevent some HTTPS man-in-the-middle attacks. Ensure your client sets the `Referer:` header appropriately (matching the allowed hosts list entered during setup) when making POST requests (including login), or all such requests will fail with 403 Forbidden error responses, even with the appropriate CSRF tokens.

#### JSON content headers

Certain IWS-Demo API endpoints use the value of the `Accept:` header to determine the content type of the response, including errors. To consistently receive responses with content type `application/json`, set the header `Accept: application/json` on all requests.

If using `curl`, this behavior can be enabled using the following command-line options:
```
curl -H 'Accept: application/json' <url>
```

#### POST request formats

IWS-Demo API endpoints which accept POST requests allow fields to be encoded as a JSON object, or as more typical URL-encoded or multipart forms. JSON-encoded request bodies will be processed as such if the `Content-Type: application/json` header is set.

If using `curl`, this behavior can be enabled using the following command-line options:
```
curl -H 'Content-Type: application/json' <url>
```

To enter a JSON-encoded request body from stdin using `curl`:
```
curl -H 'Content-Type: application/json' --data-binary @- <url>
{<JSON request body>}
```

Please note the above CSRF and Referer request header requirements as well.

### Testing your installation

#### Local

Several operations are available with the `testdata.py` script in the `iws/` directory of your IWS-Demo installation. The following commands assume any configured virtualenv is active, and the current directory is `/path/to/iws-demo/iws/`

A summary of clients (equivalent to the `/featreq/client/` endpoint) will be printed using:
```
./testdata.py
```

To additionally list open requests for each client, use the `-f` or `--full` options.

Generic test data can be initialized with the `-b` or `--build-data` options. This will add a number of clients and open requests, which can be queried, updated, and closed as desired.

**Note:** `testdata.py` operates purely locally, and does **not** test connectivity or web configuration. No active webserver is required, and all requests are processed directly by the IWS-Demo application, bypassing all uWSGI and/or webserver layers. No authentication is performed, and the default superuser `iws-admin` is used for all queries.

#### Remote

A wrapper script for `curl` is included in the `curl/` directory, as `iws-curl`. This tool automates the above-mentioned command-line options for `curl` to ease raw request testing, by adding necessary headers, storing cookies, and extracting CSRF tokens.

For GET requests, eg:
```
./iws-curl get https://iws.example.com/featreq/client/
```

For POST requests, reading JSON-formatted data from stdin, eg:
```
./iws-curl post https://iws.example.com/featreq/req/
```

#### Authentication "by hand" walkthrough

Assuming the following:
* IWS-Demo is installed and configured
* The server is available at `https://iws.example.com`
* The current directory is `/path/to/iws-demo/curl/`
* The default superuser `iws-admin` is active

First, we have to GET the current authentication state, which includes the CSRF token. `iws-curl` parses the token from the cookies file directly, but for general purpose use it is available in the response from the `/featreq/auth/` API endpoint.
```
./iws-curl get https://iws.example.com/featreq/auth/
```

The response should be similar to:
```
{
 "logged_in": false,
 "username": "",
 "full_name": "[anonymous]",
 "csrf_token": "yKXGK4x6VwGDmaYo4nnT34UhhVG4S7o9",
 "session_expiry": 1209600
}
```

This indicates that we are not logged in. Requests to any other endpoint will give a 403 Forbidden response:
```
{
 "status_code": 403,
 "error": "Not logged in or session expired"
}
```

In order to log in, we have to send a POST request to the same endpoint, with our username and password. The initial command is:
```
./iws-curl post https://iws.example.com/featreq/auth/
```
As `iws-curl` reads POST data from stdin, we need to enter it directly (or redirect from a file or pipe). If directly entering on the command line, `iws-curl` will wait for input. Enter the following:
```
{"action":"login","username":"iws-admin","password":"<your-password-here>"}
```
Then press `Ctrl-D` (once or twice depending on shell configuration) to signal EOF. If the credentials match, the response should be similar to:
```
{
 "logged_in": true,
 "username": "iws-admin",
 "full_name": "[user iws-admin]",
 "csrf_token": "Z9hxB5zYv0cuI70eAOjcxNnxEOI6uvOh",
 "session_expiry": 86400
}
```
Note that the CSRF token changes upon successful login. (It does not change, however, either on logout or on an unsuccessful login attempt, assuming cookies are enabled.)

If the credentials do not match, the response is a slightly different 403:
```
{
 "status_code": 403,
 "error": "Login failed"
}
```

Once logged in, we can access all API endpoints as desired. For example, to list available clients:
```
./iws-curl get https://iws.example.com/featreq/auth/
```
We should receive a response similar to:
```
{
 "client_count": 3,
 "client_list": [
  {
   "id": "37f25a77-3834-4adb-b1ff-3ed95f431fc6",
   "name": "Client B",
   "open_count": 6,
   "closed_count": 0
  },
  {
   "id": "4f5f8edd-5251-4e3f-b5ba-a481feb60ada",
   "name": "Client A",
   "open_count": 6,
   "closed_count": 0
  },
  {
   "id": "c7192bc4-5935-48f2-a75b-015bec84742e",
   "name": "Client C",
   "open_count": 6,
   "closed_count": 0
  }
 ]
}
```

To logout, the `/featreq/auth/` endpoint is used again. The currently logged-in username must be supplied as well.
```
./iws-curl post https://iws.example.com/featreq/auth/
```
And enter:
```
{"action":"logout","username":"iws-admin"}
```
Then press `Ctrl-D` (1x or 2x as above) for EOF. Expected response:
```
{
 "logged_in": false,
 "username": "",
 "full_name": "[anonymous]",
 "csrf_token": "Z9hxB5zYv0cuI70eAOjcxNnxEOI6uvOh",
 "session_expiry": 1209600
}
```
Again, note that the CSRF token remains the same as when logged in. The session cookie will differ, however, and access will still be denied to endpoints other than `/featreq/auth/`.
