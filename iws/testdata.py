#!/usr/bin/env python3

import os, sys
import datetime, time, json, getpass
from collections import OrderedDict

# Defaults/globals

userinfo = OrderedDict([
    ('username', 'iws-admin'),
    ('password', None),
    ('csrf_token', None)])
CON_TYPE = 'application/json'
BASEURL='/featreq/'

# Shortcuts

def getjson(client, getpath, getdata=None, expcode=200):
    resp = client.get(getpath, getdata, follow=True)
    assert resp.status_code == expcode
    return json.loads(resp.content.decode(), object_pairs_hook=OrderedDict)

def postjson(client, postpath, postdata=None, expcode=200):
    resp = client.post(
        postpath,
        json.dumps(postdata).encode(),
        content_type=CON_TYPE,
        HTTP_X_CSRFTOKEN=userinfo['csrf_token'])
    assert resp.status_code == expcode
    return json.loads(resp.content.decode(), object_pairs_hook=OrderedDict)

# Test funcs

def login(client):
    authurl = BASEURL + 'auth/'
    # Get current user status
    respobj = getjson(client, authurl)

    # Update CSRF token
    userinfo['csrf_token'] = respobj['csrf_token']

    # Check if logged in (shouldn't be)
    if respobj['logged_in'] is False:
        sys.stderr.write('Logging in as {0}...\n'.format(userinfo['username']))
        loginobj = postjson(client, authurl, {
            'action': 'login',
            'username': userinfo['username'],
            'password': userinfo['password']})

        # Check if login successful
        if loginobj['logged_in'] is not True:
            raise RuntimeError('Login unsuccessful!')

        # Update CSRF token again
        userinfo['csrf_token'] = loginobj['csrf_token']

        sys.stderr.write('Successfully logged in as {0}\n'.format(loginobj['username']))

def listclients(client):
    cliurl = BASEURL + 'client/'

    # Get and return client list
    respobj = getjson(client, cliurl)
    assert 'client_list' in respobj
    return respobj['client_list']

def buildtestdata(client):
    # Templates
    titlestr = 'Test {0}{1}'
    descstr = 'Test feature request, number {0}{1}'
    urlstr = 'http://test{0}{1}.com'
    areas = [ v for v in prodareas().keys() ]
    basedt = datetime.datetime.now(datetime.timezone.utc).replace(
        hour=12, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)

    # Create test requests
    for x in 'AB':
        cl = ClientInfo.objects.get(name='Client {0}'.format(x))
        for y in range(1, 7):
            dtgt = basedt + datetime.timedelta(days=y)
            reqargs = {}
            reqargs['title'] = titlestr.format(x, y)
            reqargs['desc'] = descstr.format(x, y)
            reqargs['ref_url'] = urlstr.format(x.lower(), y)
            reqargs['prod_area'] = areas[random.randint(0, len(areas)-1)]
            OpenReq.objects.newreq('rn', cl, 1, dtgt, **reqargs)
            time.sleep(1.0)

if __name__ == "__main__":
    # Django environment setup
    # sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iws.settings')
    import django
    django.setup()

    # Now we can access application stuff
    from django.test import Client

    # TODO: command-line option for username
    # TODO: command-line option for building test data

    # Get password to use
    userinfo['password'] = getpass.getpass(prompt='Password for {0}: '.format(userinfo['username']))

    # Create test client
    cl = Client(enforce_csrf_checks=True, HTTP_ACCEPT=CON_TYPE)

    # Login
    login(cl)
    print()

    # Get and print client list
    cllist = listclients(cl)
    cllist.sort(key=lambda x: x['name'].lower())
    print('Client list:')
    for c in cllist:
        print(c['id'], c['name'])

