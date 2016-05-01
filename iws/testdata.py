#!/usr/bin/env python3

import os, sys
import datetime, time, json, getpass, argparse
from collections import OrderedDict
from django.test import Client
from django.test.utils import override_settings
from featreq.utils import approxdatefmt

# Defaults/globals

userinfo = OrderedDict([
    ('username', 'iws-admin'),
    ('password', None),
    ('csrf_token', None)])

CON_TYPE = 'application/json'
BASEURL='/featreq/'


# Shortcuts

@override_settings(DEBUG=True)
def getjson(client, getpath, getdata=None, expcode=200, assertcode=True):
    resp = client.get(getpath, getdata, follow=True)
    if assertcode:
        assert resp.status_code == expcode
    return json.loads(resp.content.decode(), object_pairs_hook=OrderedDict)

@override_settings(DEBUG=True)
def postjson(client, postpath, postdata=None, expcode=200, assertcode=True):
    resp = client.post(
        postpath,
        json.dumps(postdata).encode(),
        content_type=CON_TYPE,
        HTTP_X_CSRFTOKEN=userinfo['csrf_token'])
    if assertcode:
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

def testlogin(client):
    urlstr = BASEURL + 'auth/'
    # Get current user status
    respobj = getjson(client, urlstr)

    # Update CSRF token
    userinfo['csrf_token'] = respobj['csrf_token']

    # Check if logged in (shouldn't be)
    if respobj['logged_in'] is False:
        sys.stderr.write('Logging in as {0}...\n'.format(userinfo['username']))

        # Get password to use
        userinfo['password'] = getpass.getpass()

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
    else:
        sys.stderr.write('Logged in as {0}\n'.format(respobj['username']))

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

def buildtestclients(client, tocreate='ABC'):
    urlstr = BASEURL + 'client/'

    # Templates
    name = 'Client {0}'
    con_name = 'Person {0}'
    con_mail = 'person{0}@client{0}.com'

    # Create test clients
    for x in tocreate:
        postdict = {
            'action': 'create',
            'name': name.format(x),
            'con_name': con_name.format(x),
            'con_mail': con_mail.format(x.lower())
        }
        respobj = postjson(client, urlstr, postdict, expcode=201)
        assert 'client' in respobj
        clobj = respobj['client']
        print('Created client: {0}, id: {1}\n'.format(clobj['name'], clobj['id']))

def buildtestdata(client):
    # Templates
    title = 'Test request {0}{1}'
    desc = 'Test feature request, number {0}{1}.\nOpened by "testdata.py"'
    ref_url = 'http://test-{0}{1}.com'
    areas = ['Billing', 'Reports', 'Claims', 'Policies']
    basedt = datetime.datetime.now(datetime.timezone.utc).replace(
        hour=12, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    statuses = ['Complete', 'Rejected', 'Deferred']
    reasons = ['Request fulfilled', 'Not feasible', 'Dependent on other feature']

    # Get clients
    respobj = getjson(client, BASEURL + 'client/')
    assert 'client_list' in respobj
    cllist = respobj['client_list']

    # Clients we have
    clset = set(c['name'] for c in cllist)
    # Clients to add
    cladd = []
    for x in 'ABC':
        if 'Client {0}'.format(x) not in clset:
            cladd.append(x)
    # Build test clients if req'd
    if cladd:
        buildtestclients(client, cladd)
        # Retry getting clients
        respobj = getjson(client, BASEURL + 'client/')
        assert 'client_list' in respobj
        cllist = respobj['client_list']

    # Filter out other clients, and sort
    cllist = [ c for c in cllist if c['name'] in {'Client A', 'Client B', 'Client C'} ]
    cllist.sort(key=lambda c: c['name'])

    # Get existing reqs
    respobj = getjson(client, BASEURL + 'req/')
    assert 'req_list' in respobj
    # Truncate titles for comparison in loop below
    trunclen = len(title.format('A', '1'))
    reqset = set(fr['title'][:trunclen] for fr in respobj['req_list'])

    # To open, per client
    cldict = OrderedDict([ (c['id'], []) for c in cllist ])

    # Create test requests
    maxrange = 15
    for x in range(len(cllist)):
        c = cllist[x]
        letter = c['name'][-1]
        toopen = []
        for y in range(1, maxrange+1):
            titlestr = title.format(letter, y)
            if titlestr not in reqset:
                reqargs = {
                    'action': 'create',
                    'title': titlestr,
                    'desc': desc.format(letter, y),
                    'ref_url': ref_url.format(letter.lower(), y),
                    'prod_area': areas[((maxrange * x) + y - 1) % len(areas)]
                }
                respobj = postjson(client, BASEURL + 'req/', reqargs, expcode=201)
                assert 'req' in respobj
                sys.stderr.write('Created request "{0}", id {1}\n'.format(
                    respobj['req']['title'], respobj['req']['id']))
                toopen.append(respobj['req']['id'])
                # Sleep to stagger creation times
                time.sleep(1.0)
        # Add to queue
        cldict[c['id']].extend(toopen)
        sys.stderr.flush()

    # Open requests per client
    for clid, toopen, offset in zip(cldict.keys(), cldict.values(), range(0, len(cldict))):
        if toopen:
            sys.stderr.write('Opening {0} requests for client id {1}\n'.format(len(toopen), clid))
            for req_id, dt in zip(toopen, range(0, len(toopen))):
                dtgt = approxdatefmt(basedt + datetime.timedelta(days=(dt * 2 + offset)))
                reqargs = {
                    'action': 'open',
                    'req_id': req_id,
                    'priority': 1,
                    'date_tgt': dtgt
                }
                respobj = postjson(client, BASEURL + 'client/' + clid + '/open/', reqargs)
                assert 'client' in respobj
                # Sleep to stagger open times
                time.sleep(1.0)
        else:
            sys.stderr.write('No test requests to open for client id {0}\n'.format(clid))
        sys.stderr.flush()

    # TODO: cross-open some requests
    # TODO: close some requests
    sys.stderr.write('\n')
    sys.stderr.flush()

if __name__ == "__main__":
    # Parse cmdline args
    # TODO: command-line option for username
    parser = argparse.ArgumentParser(description='List and build test data')
    parser.add_argument('-b', '--build-data', action='store_true', dest='builddata', help='build test data')
    parser.add_argument('-f', '--full', action='store_true', help='print feature requests per client')
    args = parser.parse_args()

    # Django environment setup
    # sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iws.settings')
    import django
    django.setup()
    
    # Now we can access application stuff
    from django.contrib.auth.models import User

    # Create test client
    cl = Client(enforce_csrf_checks=True, HTTP_ACCEPT=CON_TYPE)

    # Login
    # Force login for now to skip password
    user = User.objects.get(username=userinfo['username'])
    cl.force_login(user)
    testlogin(cl)
    print()

    # Optionally build any missing test data
    if args.builddata:
        buildtestdata(cl)

    # Get, store, and print client list
    cllist = listclients(cl)
    cllist.sort(key=lambda x: x['name'].lower())

    printrows(
        [ (c['name'], c['open_count'], c['closed_count'], c['id']) for c in cllist ],
        ('Client name', 'Open', 'Closed', 'Client ID'))
    print()

    # Store for later
    cldict = OrderedDict((c['id'], c) for c in cllist)

    if args.full:
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
            printlist = [ [ fr['priority'], frdict[fr['req']['id']]['title'], fr['req']['id'] ] for fr in frlist ]

            # Now print
            printrows(printlist, ('Priority', 'Title', 'Request ID'))
            print()
