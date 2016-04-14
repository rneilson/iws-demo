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

CLIENTFMT = '{name:12s}\t{id:36s}'

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

def printrows(rows, headers, spacer='  '):
    if rows:
        # Get column widths per field
        widths = [ max(map(lambda x: len(str(x)), col)) for col in zip(*rows) ]
        # Check if headers are longer
        widths = [ max(width, len(hd)) for width, hd in zip(widths, headers) ]
    else:
        widths = [ len(hd) for hd in headers ]

    # Print headers
    print(spacer.join(header.ljust(width) for header, width in zip(headers, widths)))
    # Print separators
    print(spacer.join('-' * width for width in widths))
    # Print rows
    for row in rows:
        print(spacer.join(str(col).ljust(width) for col, width in zip(row, widths)))

# Test funcs

def login(client):
    urlstr = BASEURL + 'auth/'
    # Get current user status
    respobj = getjson(client, urlstr)

    # Update CSRF token
    userinfo['csrf_token'] = respobj['csrf_token']

    # Check if logged in (shouldn't be)
    if respobj['logged_in'] is False:
        sys.stderr.write('Logging in as {0}...\n'.format(userinfo['username']))
        loginobj = postjson(client, urlstr, {
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
    urlstr = BASEURL + 'client/'

    # Get and return client list
    respobj = getjson(client, urlstr)
    assert 'client_list' in respobj
    return respobj['client_list']

def listreqs(client):
    urlstr = BASEURL + 'req/'

    # Get and return client list
    respobj = getjson(client, urlstr)
    assert 'req_list' in respobj
    return respobj['req_list']

def listreqsbyclient(client, client_id, listopen=True):
    if listopen:
        urlstr = BASEURL + 'client/' + client_id + '/open/'
        respobj = getjson(client, urlstr)
        assert 'client' in respobj
        assert 'open_list' in respobj['client']
        return respobj['client']['open_list']
    else:
        urlstr = BASEURL + 'client/' + client_id + '/closed/'
        respobj = getjson(client, urlstr)
        assert 'client' in respobj
        assert 'closed_list' in respobj['client']
        return respobj['client']['closed_list']

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

    # Get, store, and print client list
    cllist = listclients(cl)
    cllist.sort(key=lambda x: x['name'].lower())

    printrows([ (c['name'], c['id']) for c in cllist ], ('Client name', 'Client ID'))
    print()

    # Store for later
    cldict = OrderedDict((c['id'], c) for c in cllist)

    # Get featreqs
    frdict = { fr['id']:fr for fr in listreqs(cl) }

    # Get and print open featreq list per client
    for c in cldict.values():
        frlist = listreqsbyclient(cl, c['id'])
        frlist.sort(key=lambda x: x['priority'])

        # Per-client header
        headstr = '{0} open requests:\n'.format(c['name'])
        print(headstr)

        # Have to make list of lists, since pulling in title
        printlist = [ [ fr['priority'], frdict[fr['req_id']]['title'], fr['req_id'] ] for fr in frlist ]

        # Now print
        printrows(printlist, ('Priority', 'Title', 'Request ID'))
        print()
