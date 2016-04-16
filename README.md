## IWS-Demo

This is a demonstration web application for creating and managing feature requests for a group of clients, written in Python using Django, and implementing a RESTful JSON API backend.

Please note that this is a work in progress, and the API is not considered stable at this time. A demonstration frontend is in development.

### API

Please refer to API.md for API endpoint documentation.

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
