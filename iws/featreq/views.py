import datetime, json
from collections import OrderedDict
from functools import partial
from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect,\
    HttpResponseNotFound, HttpResponseNotAllowed, HttpResponseBadRequest, HttpResponseForbidden
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse as urlreverse
from django.db.models import Count
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt, requires_csrf_token
from django.middleware.csrf import get_token as csrf_get_token
from django.contrib.auth import authenticate, login, logout
from .models import FeatureReq, ClientInfo, OpenReq, ClosedReq
from .utils import approxnow, tojsondict, qset_vals_tojsonlist

## Common vars

# Default session exipiry time
# 24h for testing purposes at present
SESSION_EXPIRY = 86400
WEBVIEW_URL = '/webview/'

# Default 404 JSON response dict
# Views may add extra information, or JSONify and send as-is
json404 = OrderedDict([('status_code', 404), ('error', 'Resource not found')])
json404str = json.dumps(json404, indent=1) + '\n'
json_contype = 'application/json'
plain_contype = 'text/plain'

# OpenReq and ClosedReq modified fields and qset_vals_tojsonlist partials
openreq_byreq_fields = OpenReq.fields.copy()
del openreq_byreq_fields['req_id']
# openreq_byreq_partial = partial(
#     qset_vals_tojsonlist, 
#     fields=openreq_byreq_fields.keys(), 
#     fcalls=openreq_byreq_fields.values())

closedreq_byreq_fields = ClosedReq.fields.copy()
del closedreq_byreq_fields['req_id']
# closedreq_byreq_partial = partial(
#     qset_vals_tojsonlist, 
#     fields=closedreq_byreq_fields.keys(), 
#     fcalls=closedreq_byreq_fields.values())

client_with_counts_dict = OrderedDict([
    ('id', ClientInfo.fields['id']),
    ('name', None),
    ('open_count', None),
    ('closed_count', None)
])

openreq_byclient_fields = OpenReq.fields.copy()
del openreq_byclient_fields['client_id']
#openreq_byclient_fields.move_to_end('req_id')
#del openreq_byclient_fields['req_id']
#openreq_byclient_fields['req'] = tojsondict

closedreq_byclient_fields = ClosedReq.fields.copy()
del closedreq_byclient_fields['client_id']
#closedreq_byclient_fields.move_to_end('req_id')
#del closedreq_byclient_fields['req_id']
#closedreq_byclient_fields['req'] = tojsondict

## Shortcut funcs

def req_is_json(request):
    if json_contype in request.META.get('HTTP_ACCEPT', '').lower() or\
        json_contype in request.META.get('CONTENT_TYPE', '').lower():
        return True
    else:
        return False

def req_is_plain(request):
    if request.META.get('HTTP_ACCEPT', '').lower() == plain_contype:
        return True
    else:
        return False

def getusername(request):
    '''Extracts username from request, or provides default.'''
    unknown_user = 'UNKNOWN'
    try:
        username = request.user.get_username()
    except AttributeError:
        # TODO: raise exception instead(?)
        username = unknown_user
    else:
        if not username:
            # TODO: raise exception instead(?)
            username = unknown_user
    return username

def badrequest(request, errormsg, field=None, adderr=None):
    '''Constructs 400 Bad Request response with given error message.'''

    if req_is_plain(request):
        if field:
            respstr = 'Status code: 400\nError in field: {0}\nError message: {1}\n'.format(field, str(errormsg))
        else:
            respstr = 'Status code: 400\nError message: {0}\n'.format(str(errormsg))
        return HttpResponseBadRequest(respstr, content_type=plain_contype)
    # if req_is_json(request):
    else:
        # Create reponse payload
        errordict = OrderedDict([
            ('status_code', 400),
            ('error', str(errormsg))
        ])
        if field:
            errordict['field'] = str(field)
        if adderr:
            errordict.update(adderr)
        jsonbytes = (json.dumps(errordict, indent=1) + '\n').encode('utf-8')
        return HttpResponseBadRequest(jsonbytes, content_type=json_contype)

def forbidden(request, errormsg='Not authorized', adderr=None):
    '''Constructs 403 Forbidden response with given error message.
    If given, adderr must be a dict of additional fields to append to the
    error response.
    '''

    if req_is_plain(request):
        errorstr = 'Status code: 403\nError message: {0}\n'.format(errormsg)
        return HttpResponseForbidden(errorstr, content_type=plain_contype)
    # if req_is_json(request):
    else:
        errordict = OrderedDict([
            ('status_code', 403),
            ('error', errormsg)])
        if adderr:
            errordict.update(adderr)
        return HttpResponseForbidden(json.dumps(errordict, indent=1)+'\n', content_type=json_contype)

def getargsfrompost(request, fieldnames=None, required=None, aslist=None, asint=None):
    '''Extracts ordered dict of arguments from POST request. Requests with
    content type 'application/json' will use the request body decoded from
    JSON; all other requests will use Django's QueryDict as the source.

    Returns an OrderedDict, ordered by fieldnames if given.

    If fieldnames is specified, only those fields will be extracted.

    If required is specified, ValueError will be raised if any fieldnames
    in required are missing. For best efficiency, pass as a set instead of
    a list or tuple.

    If aslist is specified, any fieldnames in aslist will be stored in the
    returned dictionary as lists, even if there is only one value. For best
    efficiency, pass as a set instead of a list or tuple.

    If asint is specified, any fieldnames in asint will be coerced to int,
    or a list of ints if the fieldname is also in aslist, and any ValueError
    caught will be re-raised as ValueError with the fieldname in the
    exception message.
    '''
    if json_contype in request.META.get('CONTENT_TYPE', '').lower():
        # Specific codepath for JSON, since we can decode into the form
        # of our own choosing

        # Set encoding, falling back to UTF-8
        encoding = request.encoding
        if not encoding:
            encoding = 'utf-8'

        # If fieldnames given, we need to populate and order the returned
        # dict, so we'll decode JSON as a regular dict and transfer over
        # values field-by-field
        if fieldnames:
            respdict = OrderedDict()
            tmpdict = json.loads(request.body.decode(encoding))
            for fn in fieldnames:
                try:
                    fv = tmpdict[fn]
                except KeyError:
                    pass
                else:
                    respdict[fn] = fv
        # If no fieldnames given, we decode straight into an OrderedDict
        else:
            respdict = json.loads(request.body.decode(encoding), object_pairs_hook=OrderedDict)

        # Now we check the output
        # Check required fields
        if required:
            for fn in required:
                if fn not in respdict:
                    raise ValueError('Required field {0} missing'.format(fn))
        # Check aslist fields
        if aslist:
            for fn in aslist:
                try:
                    fv = respdict[fn]
                except KeyError:
                    pass
                else:
                    if not isinstance(fv, list):
                        if fv is None:
                            respdict[fn] = []
                        else:
                            respdict[fn] = [fv]
        # Check asint fields
        if asint:
            for fn in asint:
                try:
                    fv = respdict[fn]
                except KeyError:
                    pass
                else:
                    if isinstance(fv, list):
                        try:
                            fv = [ int(v) for v in fv ]
                        except (ValueError, TypeError) as e:
                            raise TypeError('Cannot convert list item in field {0} to int: {1}'.format(fn, str(e)))
                    else:
                        try:
                            fv = int(fv)
                        except (ValueError, TypeError) as e:
                            raise TypeError('Cannot convert field {0} to int: {1}'.format(fn, str(e)))
                    respdict[fn] = fv

        # Now we can return the final product
        return respdict

    else:
        # We use a different approach to non-JSON requests, as the request
        # data is in QueryDict form -- we do aslist and asint checks per
        # field while building the OrderedDict, and check required beforehand

        # Check required
        if required:
            for fn in required:
                if fn not in request.POST:
                    raise ValueError('Required field {0} missing'.format(fn))

        # Use the QueryDict's keys as fieldname list if not provided
        if not fieldnames:
            fieldnames = request.POST.keys()

        # Give aslist and asint empty sets to save ourselves extra existence
        # checks while iterating
        if not aslist:
            aslist = set()
        if not asint:
            asint = set()

        # Now we iterate over the fieldnames, and put them in order, checking
        # aslist and asint as we go
        respdict = OrderedDict()
        for fn in fieldnames:
            if fn in request.POST:
                if fn in aslist:
                    # Get the list form
                    fv = request.POST.getlist(fn)
                    # Convert to list of ints if required
                    if fn in asint:
                        try:
                            fv = [ int(v) for v in fv ]
                        except (ValueError, TypeError) as e:
                            raise TypeError('Cannot convert list item in field {0} to int: {1}'.format(fn, str(e)))
                else:
                    # Get the single item form
                    fv = request.POST.get(fn)
                    # Convert to int if required
                    if fn in asint:
                        try:
                            fv = int(fv)
                        except (ValueError, TypeError) as e:
                            raise TypeError('Cannot convert field {0} to int: {1}'.format(fn, str(e)))
                # Add final form to response
                respdict[fn] = fv

            # We've already checked required fields, so we don't have to
            # handle missing fields here

        # Now we can return the final product
        return respdict

def getfieldsfromget(
    request, empty=None, allfields=None, allowed=None,
    fieldsep=',', fieldname='fields', allfieldname='all'):
    '''Get field values from query string in request. Returns list of values.

    If there are no fields of fieldname in the query, will return value of
    param empty.

    If there is a field value of allfieldname (default is 'all') in the query,
    will return value of param allfields.

    If allowed is specified, field values will be checked for inclusion, and
    only values in allowed will be returned.

    If fieldsep is specified (default is ','), field values will be split
    using fieldsep as the separator. Note: this is done after checking for the
    value of allfieldname.
    '''

    # Get requested fieldname list
    fields = request.GET.getlist(fieldname)

    # Default fields if none provided
    if not fields:
        # None (default) will typically get fields from model
        fields = empty
    # All fields (must be last parameter in query string)
    elif allfieldname in fields:
        # None (default) will typically get fields from model
        fields = allfields
    # Split fields if req'd
    elif fieldsep:
        newfields = []
        for fv in fields:
            newfields.extend(fv.split(fieldsep))
        fields = newfields

    # Filter by allowed if given
    if fields and allowed:
        fields = [ fv for fv in fields if fv in allowed ]

    return fields

def prettifyjson(request, response):
    resp = render(request, 'featreq/json.html', {'response': response})
    resp.status_code = response.status_code
    resp.reason_phrase = response.reason_phrase
    return resp

## Decorators

def allow_methods(methods, usejson=True):
    '''Decorator for views.
    Returns HttpResponseNotAllowed object with decorated parameters.
    '''
    def wrap(f):
        methodset = set(methods)
        respstr = 'Method {0} not available here.'
        if usejson:
            def wrapped(request, *args, **kwargs):
                if request.method in methodset:
                    return f(request, *args, **kwargs)
                else:
                    errordict = OrderedDict([
                        ('status_code', 405),
                        ('error', respstr.format(request.method))
                    ])
                    jsonbytes = (json.dumps(errordict, indent=1) + '\n').encode('utf-8')
                    return HttpResponseNotAllowed(methods, jsonbytes, content_type=json_contype)
        else:
            def wrapped(request, *args, **kwargs):
                if request.method in methodset:
                    return f(request, *args, **kwargs)
                else:
                    return HttpResponseNotAllowed(methods, respstr.format(request.method)+'\n')
        return wrapped
    return wrap

def auth_required(f):
    '''Decorator for views. Checks that user is authenticated, returns
    403 Forbidden response if not.
    '''
    def wrapped(request, *args, **kwargs):
        if request.user.is_authenticated():
            return f(request, *args, **kwargs)
        else:
            return forbidden(request, 'Not logged in or session expired')
    return wrapped

def makepretty(f):
    '''Decorator for views. Checks for redirect response, and if not,
    returns either raw JSON or the prettified version.
    '''
    def wrapped(request, *args, **kwargs):
        if req_is_json(request):
            return f(request, *args, **kwargs)
        else:
            resp = f(request, *args, **kwargs)
            # Return redirects without modification
            if (resp.status_code >= 300 and resp.status_code < 400) or \
                resp['Content-Type'] == 'text/plain':
                return resp
            else:
                return prettifyjson(request, resp)
    return wrapped


## View funcs

@makepretty
@allow_methods(['GET'])
def index(request):
    if not request.user.is_authenticated():
        if req_is_json(request):
            nexturl = urlreverse('featreq-auth') + '?next=' + urlreverse('featreq-index')
            return HttpResponseRedirect(nexturl)
        else:
            nexturl = urlreverse('featreq-login') + '?next=' + WEBVIEW_URL
            return HttpResponseRedirect(nexturl)
    else:
        if req_is_json(request):
            username = request.user.get_username()
            try:
                fullname = request.user.get_full_name()
            except AttributeError:
                fullname = '[user {0}]'.format(username)
            if not fullname:
                fullname = '[user {0}]'.format(username)
            # if req_is_json(request):
            respdict = OrderedDict([
                ('username', username),
                ('full_name', fullname),
                ('session_expiry', request.session.get_expiry_age())
            ])
            return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type=json_contype)
        else:
            return HttpResponseRedirect(WEBVIEW_URL)

@ensure_csrf_cookie
@requires_csrf_token
@allow_methods(['GET'])
def weblogin(request):
    # Check for 'next' field
    nexturl = getfieldsfromget(request, empty=None, fieldsep=None, fieldname='next', allfieldname=None)
    # Get first value
    if nexturl:
        nexturl = nexturl[0]
    else:
        nexturl = urlreverse('featreq-login')
    # Render template and return
    return render(request, 'featreq/login.html', {'nexturl': nexturl})

@ensure_csrf_cookie
@requires_csrf_token
@allow_methods(['GET', 'POST'])
def apiauth(request):

    @makepretty
    def _authresp(request):
        # Check for 'next' field
        nexturl = getfieldsfromget(request, empty=[], fieldsep=None, fieldname='next', allfieldname=None)

        if nexturl:
            if request.user.is_authenticated():
                return HttpResponseRedirect(nexturl[0])
            else:
                if req_is_json(request):
                    return forbidden(request, 'Not logged in or session expired', {'next': nexturl[0]})
                else:
                    redir = urlreverse('featreq-login') + '?next=' + nexturl[0]
                    return HttpResponseRedirect(redir)
        else:
            loggedin = request.user.is_authenticated()
            username = request.user.get_username()
            try:
                fullname = request.user.get_full_name()
            except AttributeError:
                fullname = '[anonymous]'.format(username)
            if not fullname:
                fullname = '[user {0}]'.format(username)

            # Check for text/plain
            reqfmt = getfieldsfromget(request, fieldsep=None, fieldname='format', allfieldname=None)
            if (reqfmt and reqfmt[0] == 'plain') or req_is_plain(request):
                histr = 'Logged in: {0}\nUsername: {1}\nFull name: {2}\nCSRF token: {3}\nSession expiry: {4}s\n'.format(
                    loggedin, username, fullname, csrf_get_token(request), request.session.get_expiry_age())
                return HttpResponse(histr, content_type='text/plain')
            else:
                respdict = OrderedDict([
                    ('logged_in', loggedin),
                    ('username', username),
                    ('full_name', fullname),
                    ('csrf_token', csrf_get_token(request)),
                    ('session_expiry', request.session.get_expiry_age()),
                ])
                return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type=json_contype)

    if request.method == 'GET':
        return _authresp(request)

    elif request.method == 'POST':
        # Get login args
        try:
            postargs = getargsfrompost(
                request,
                fieldnames=('action', 'username', 'password'),
                required={'action', 'username'}
            )
        except ValueError as e:
            if 'CONTENT_TYPE' in request.META:
                adderr = {'content_type': request.META['CONTENT_TYPE']}
            else:
                adderr = None
            return badrequest(request, e, adderr=adderr)

        action = postargs['action'].lower()

        if action == 'login':
            # Ensure password supplied
            if 'password' not in postargs:
                return badrequest(request, 'No password given', 'password')

            # Log out current user, if any
            logout(request)

            # Authenticate user and return result
            user = authenticate(username=postargs['username'], password=postargs['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    request.session.set_expiry(SESSION_EXPIRY)
                    # TODO: return something directly?
                    return _authresp(request)
                else:
                    # TODO: is this a security hole? Should we just return "Login failed"?
                    return forbidden(request, 'User {0} is disabled'.format(user.get_username()))
            else:
                return forbidden(request, 'Login failed')
        elif action == 'logout':
            # Make sure usernames (given and stored) match
            if postargs['username'] != request.user.get_username():
                return forbidden(request, 'Given username does not match current user',
                    {'username': postargs['username']})
            # Log out user
            logout(request)
            return _authresp(request)
        else:
            return badrequest(request, 'Invalid action: {0}'.format(action), 'action')

@makepretty
@auth_required
@allow_methods(['GET', 'POST'])
def reqindex(request):
    # TODO: add filter options

    if request.method == 'GET':
        # Get requested fieldname list
        fields = getfieldsfromget(request, empty=['id', 'title'], allowed=FeatureReq.fields)

        # Get featreqs
        frlist = qset_vals_tojsonlist(FeatureReq.objects, fields)

        # Construct response
        respdict = OrderedDict([('req_count', len(frlist)), ('req_list', frlist)])
        return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type=json_contype)

    elif request.method == 'POST':
        # Get user
        # TODO: try/except (once auth in place)
        username = getusername(request)

        # Get args
        try:
            # TODO: remove title and desc from required if any additional
            # actions get defined
            postargs = getargsfrompost(request,
                fieldnames=('action', 'id', 'title', 'desc', 'ref_url', 'prod_area'),
                required={'action', 'title', 'desc'}
            )
        except ValueError as e:
            return badrequest(request, e)

        # Update request
        action = postargs.pop('action').lower()
        if action == 'create':
            # Add user
            postargs['user'] = username
            postargs.move_to_end('user', last=False)

            # Attempt featreq creation and return new featreq or error
            try:
                fr = FeatureReq.objects.newreq(**postargs)
            except Exception as e:
                return badrequest(request, e)
            else:
                resp = HttpResponse(json.dumps({'req': fr.jsondict()}, indent=1)+'\n', status=201, content_type=json_contype)
                resp['Location'] = urlreverse('featreq-req-byid', kwargs={'req_id':fr.id})
                return resp
        else:
            return badrequest(request, 'Invalid action "{0}"'.format(action), field='action')

@makepretty
@auth_required
@allow_methods(['GET'])
def reqindex_ext(request, tolist):
    # TODO: add filter options

    def _getindex(request, listopen, listclosed):
        # We'll feed each FeatureReq into an OrderedDict by id, and append matching
        # OpenReqs to them
        frdict = OrderedDict()

        # Get requested fieldname list
        fields = getfieldsfromget(
            request,
            empty=['id', 'title'],
            allfields=FeatureReq.fields.keys(),
            allowed=FeatureReq.fields
        )

        # Get open, if requested
        if listopen:
            # Get all open requests, prefetching FeatureReq objects
            oreqlist = OpenReq.objects.select_related('req')
            for oreq in oreqlist:
                # Get/create featreq dict
                try:
                    fr = frdict[oreq.req_id]
                except KeyError:
                    # FeatureReq not in master dict, create JSON-compat dict and add
                    fr = oreq.req.jsondict(fields)
                    frdict[oreq.req_id] = fr
                # Get open_list from featreq dict
                try:
                    openlist = fr['open_list']
                except KeyError:
                    # OpenReq list not in featreq dict, add fresh list
                    openlist = list()
                    fr['open_list'] = openlist
                # Now add OpenReq to list (minus redundant req_id)
                openlist.append(oreq.jsondict(openreq_byreq_fields.keys(), openreq_byreq_fields.values()))

        # Get closed, if requested
        if listclosed:
            # Get all closed requests, prefetching FeatureReq objects
            creqlist = ClosedReq.objects.select_related('req')
            for creq in creqlist:
                # Get/create featreq dict
                try:
                    fr = frdict[creq.req_id]
                except KeyError:
                    # FeatureReq not in master dict, create JSON-compat dict and add
                    fr = creq.req.jsondict(fields)
                    frdict[creq.req_id] = fr
                # Get closed_list from featreq dict
                try:
                    closedlist = fr['closed_list']
                except KeyError:
                    # ClosedReq list not in featreq dict, add fresh list
                    closedlist = list()
                    fr['closed_list'] = closedlist
                # Now add ClosedReq to list (minus redundant req_id)
                closedlist.append(creq.jsondict(closedreq_byreq_fields.keys(), closedreq_byreq_fields.values()))

        # Now list-ify everything
        frlist = list(frdict.values())

        # Construct response
        respdict = OrderedDict([('req_count', len(frlist)), ('req_list', frlist)])
        return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type=json_contype)

    '''
    @allow_methods(['GET'])
    def _openindex(request):
        #if request.method == 'GET':
        return _getindex(request, listopen=True, listclosed=False)
        # TODO: add POST method?

    @allow_methods(['GET'])
    def _closedindex(request):
        #if request.method == 'GET':
        return _getindex(request, listopen=False, listclosed=True)
        # TODO: add POST method?

    @allow_methods(['GET'])
    def _allindex(request):
        return _getindex(request, listopen=True, listclosed=True)
    '''

    # Forward to appropriate inner function
    if tolist == 'open':
        return _getindex(request, listopen=True, listclosed=False)
        # return _openindex(request)
    elif tolist == 'closed':
        return _getindex(request, listopen=False, listclosed=True)
        # return _closedindex(request)
    elif tolist == 'all':
        return _getindex(request, listopen=True, listclosed=True)
        # return _allindex(request)

@makepretty
@auth_required
@allow_methods(['GET', 'POST'])
def reqbyid(request, req_id):
    # Get selected featreq
    try:
        fr = FeatureReq.objects.get(id=req_id)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(json404str, content_type=json_contype)
    else:
        if request.method == 'GET':
            # Return (ordered) dict as JSON
            return HttpResponse(json.dumps({'req': fr.jsondict()}, indent=1)+'\n', content_type=json_contype)
        elif request.method == 'POST':
            # Get user
            # TODO: try/except (once auth in place)
            username = getusername(request)

            # Get args
            try:
                postargs = getargsfrompost(request, 
                    fieldnames=('action', 'desc', 'title', 'ref_url', 'prod_area'), 
                    required={'action'}
                )
            except ValueError as e:
                return badrequest(request, e)

            # Update request
            action = postargs.pop('action')
            if action == 'update':
                # Add user
                postargs['user'] = username
                postargs.move_to_end('user', last=False)

                # Attempt update and return new featreq or error
                try:
                    fr = fr.updatereq(**postargs)
                except Exception as e:
                    return badrequest(request, e)
                else:
                    return HttpResponse(json.dumps({'req': fr.jsondict()}, indent=1)+'\n', content_type=json_contype)
            else:
                return badrequest(request, 'Invalid action "{0}"'.format(action), field='action')

@makepretty
@auth_required
def reqbyid_ext(request, req_id, tolist):

    def _getext(request, featreq, listopen=False, listclosed=False):
        # Get featreq fields
        fields = getfieldsfromget(request, empty=['id'], allowed=FeatureReq.fields)

        # Get featreq dict
        frdict = featreq.jsondict(fields)

        # Get open if requested
        if listopen:
            frdict['open_list'] = qset_vals_tojsonlist(
                featreq.open_list,
                openreq_byreq_fields.keys(),
                openreq_byreq_fields.values()
            )

        # Get closed if requested
        if listclosed:
            frdict['closed_list'] = qset_vals_tojsonlist(
                featreq.closed_list,
                closedreq_byreq_fields.keys(),
                closedreq_byreq_fields.values()
            )

        # Return dict as JSON
        return HttpResponse(json.dumps({'req': frdict}, indent=1)+'\n', content_type=json_contype)

    @allow_methods(['GET'])
    def _openext(request, featreq):
        return _getext(request, featreq, listopen=True)

    @allow_methods(['GET'])
    def _closedext(request, featreq):
        return _getext(request, featreq, listclosed=True)

    @allow_methods(['GET', 'POST'])
    def _allext(request, featreq):

        if request.method == 'GET':
            return _getext(request, featreq, listopen=True, listclosed=True)

        elif request.method == 'POST':
            # Check/get user
            username = getusername(request)

            # Check args
            try:
                postargs = getargsfrompost(
                    request,
                    fieldnames=('action', 'client_id', 'priority', 'date_tgt', 'status', 'reason'),
                    required={'action'},
                    asint={'priority'}
                )
            except ValueError as e:
                return badrequest(request, e)

            # Check action
            action = postargs.pop('action').lower()

            if action == 'open':
                try:
                    client_id = postargs.pop('client_id')
                except KeyError:
                    return badrequest(request, 'Action "open" requires field "client_id"', 'client_id')

                # Check client_id
                if not ClientInfo.objects.filter(id=client_id).exists():
                    return badrequest(request, 'No client with id {0}'.format(client_id), 'client_id')

                # Check for unsupported args
                for fn in postargs:
                    if fn not in {'priority', 'date_tgt'}:
                        del postargs[fn]

                # Put client_id back in dict under new name
                # attachreq() takes client instead of client_id
                postargs['client'] = client_id

                # Add username and req_id
                postargs['request'] = featreq
                postargs['user'] = username

                # Now attempt to attach
                try:
                    OpenReq.objects.attachreq(**postargs)
                except Exception as e:
                    return badrequest(request, e)

                # Made it this far, good to go
                # Return updated view
                return _getext(request, featreq, listopen=True, listclosed=True)

            elif action == 'update':
                try:
                    client_id = postargs.pop('client_id')
                except KeyError:
                    return badrequest(request, 'Action "update" requires field "client_id"', 'client_id')

                # Check client_id is in open list for this req
                try:
                    oreq = OpenReq.objects.get(client_id=client_id, req_id=featreq.id)
                except ObjectDoesNotExist:
                    return badrequest(request, 'Request not open for client_id {0}'.format(client_id), 'client_id')

                # Remove unsupported args
                for fn in postargs:
                    if fn not in {'priority', 'date_tgt'}:
                        del postargs[fn]

                # Add openreq
                postargs['openreq'] = oreq

                # Now attempt to update
                try:
                    OpenReq.objects.updatereq(**postargs)
                except Exception as e:
                    return badrequest(request, e)

                # Made it this far, good to go
                # Return updated view
                return _getext(request, featreq, listopen=True, listclosed=True)

            elif action == 'close':
                # Check if client specified
                try:
                    client_id = postargs.pop('client_id')
                except KeyError:
                    client_id = None
                else:
                    # Check client_id is in open list for this featreq
                    if not fr.open_list.filter(client_id=client_id).exists():
                        return badrequest(request, 'Request not open for client_id {0}'.format(client_id), 'client_id')

                # Check for unsupported args
                for fn in postargs:
                    if fn not in {'status', 'reason'}:
                        del postargs[fn]

                # Put client_id back in dict under new name
                # closereq() takes client instead of client_id
                postargs['client'] = client_id

                # Add username and req_id
                postargs['request'] = featreq
                postargs['user'] = username

                # Now attempt to close
                try:
                    ClosedReq.objects.closereq(**postargs)
                except Exception as e:
                    return badrequest(request, e)

                # Made it this far, good to go
                # Return updated view
                return _getext(request, featreq, listopen=True, listclosed=True)

            else:
                return badrequest(request, 'Invalid action "{0}"'.format(action), field='action')

    # Get selected featreq
    try:
        fr = FeatureReq.objects.get(id=req_id)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(json404str, content_type=json_contype)
    else:
        # Forward to appropriate inner function
        if tolist == 'open':
            return _openext(request, fr)
        elif tolist == 'closed':
            return _closedext(request, fr)
        elif tolist == 'all':
            return _allext(request, fr)

@auth_required
def reqredir(request, req_id):
    # Check if req_id exists
    if FeatureReq.objects.filter(id=req_id).exists():
        # Redirect to proper featreq URL
        return HttpResponsePermanentRedirect(urlreverse('featreq-req-byid', args=(req_id,)))
    else:
        return HttpResponseNotFound(json404str, content_type=json_contype)

@makepretty
@auth_required
@allow_methods(['GET', 'POST'])
def clientindex(request):
    # TODO: add filter options, additional field options
    if request.method == 'GET':
        # Get JSON-compat dicts for all clients
        # Get client id, name, and open/closed counts
        clqset = ClientInfo.objects.annotate(
            open_count=Count('open_list', distinct=True), 
            closed_count=Count('closed_list', distinct=True))
        cllist = qset_vals_tojsonlist(clqset, client_with_counts_dict.keys(), client_with_counts_dict.values())
        # Construct response
        respdict = OrderedDict([('client_count', len(cllist)), ('client_list', cllist)])
        return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type=json_contype)

    elif request.method == 'POST':
        # Get user
        # TODO: try/except (once auth in place)
        username = getusername(request)

        # Get args
        try:
            # TODO: remove title and desc from required if any additional
            # actions get defined
            postargs = getargsfrompost(request,
                fieldnames=('action', 'name', 'con_name', 'con_mail', 'id'),
                required={'action', 'name'}
            )
        except ValueError as e:
            return badrequest(request, e)

        # Update request
        action = postargs.pop('action').lower()
        if action == 'create':
            # User not recorded by newclient() at present
            # postargs['user'] = username
            # postargs.move_to_end('user', last=False)

            # Attempt client creation and return new featreq or error
            try:
                cl = ClientInfo.objects.newclient(**postargs)
            except Exception as e:
                return badrequest(request, e)
            else:
                resp = HttpResponse(json.dumps({'client': cl.jsondict()}, indent=1)+'\n', status=201, content_type=json_contype)
                resp['Location'] = urlreverse('featreq-client-byid', kwargs={'client_id':cl.id})
                return resp
        else:
            return badrequest(request, 'Invalid action "{0}"'.format(action), field='action')


@makepretty
@auth_required
@allow_methods(['GET', 'POST'])
def clientbyid(request, client_id):
    # Get selected featreq
    try:
        cl = ClientInfo.objects.get(id=client_id)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(json404str, content_type=json_contype)
    else:
        if request.method == 'GET':
            # Return (ordered) dict as JSON
            return HttpResponse(json.dumps({'client': cl.jsondict()}, indent=1)+'\n', content_type=json_contype)

        elif request.method == 'POST':
            # User not recorded by updateclient() at present
            # username = getusername(request)

            # Get args
            try:
                postargs = getargsfrompost(request, 
                    fieldnames=('action', 'name', 'con_name', 'con_mail'), 
                    required={'action'}
                )
            except ValueError as e:
                return badrequest(request, e)

            action = postargs.pop('action')
            
            # Update client
            if action == 'update':
                # Attempt update and return client details or error
                try:
                    cl = cl.updateclient(**postargs)
                except Exception as e:
                    return badrequest(request, e)
                else:
                    return HttpResponse(json.dumps({'client': cl.jsondict()}, indent=1)+'\n', content_type=json_contype)
            else:
                return badrequest(request, 'Invalid action "{0}"'.format(action), field='action')


@auth_required
def clientredir(request, client_id):
    # Check if client_id exists
    if ClientInfo.objects.filter(id=client_id).exists():
        # Redirect to proper client info URL
        return HttpResponsePermanentRedirect(urlreverse('featreq-client-byid', args=(client_id,)))
    else:
        return HttpResponseNotFound(json404str, content_type=json_contype)

@makepretty
@auth_required
def clientreqindex(request, client_id, tolist):

    def _getindex(request, client_id, listopen=False, listclosed=False):
        # Get featreq fields
        # For default we want None, so we can still test if featreq fields
        # asked for in querystring
        # If all fields requested, just use FeatureReq fields attribute
        fields = getfieldsfromget(
            request,
            empty=None,
            allfields=FeatureReq.fields.keys(),
            allowed=FeatureReq.fields
        )

        respdict = OrderedDict([('id', client_id)])

        # Get open, if requested
        if listopen:
            oreqlist = []
            # Get open reqs for client
            qset = OpenReq.objects.filter(client_id=client_id)

            # Only fetch related featreq if details requested
            if fields:
                qset = qset.select_related('req')

            for oreq in qset:
                # Get JSON-compat dict
                oreqdict = oreq.jsondict(
                    fields=openreq_byclient_fields.keys(), 
                    fcalls=openreq_byclient_fields.values()
                )

                if fields:
                    # Remove redundant req_id
                    del oreqdict['req_id']
                    # Add featreq details (with specified fields)
                    oreqdict['req'] = oreq.req.jsondict(fields)
                    # TODO: move to front?
                else:
                    # Move req_id into req sub-object
                    req_id = oreqdict.pop('req_id')
                    oreqdict['req'] = {'id': req_id}

                oreqlist.append(oreqdict)

            # Add to response
            respdict['open_list'] = oreqlist

        # Get closed, if requested
        if listclosed:
            creqlist = []
            # Get closed reqs for client
            qset = ClosedReq.objects.filter(client_id=client_id)

            # Only fetch related featreq if details requested
            if fields:
                qset = qset.select_related('req')

            for creq in qset:
                # Get JSON-compat dict
                creqdict = creq.jsondict(
                    fields=closedreq_byclient_fields.keys(), 
                    fcalls=closedreq_byclient_fields.values()
                )

                if fields:
                    # Remove redundant req_id
                    del creqdict['req_id']
                    # Add featreq details (with specified fields)
                    creqdict['req'] = creq.req.jsondict(fields)
                    # TODO: move to front?
                else:
                    # Move req_id into req sub-object
                    req_id = creqdict.pop('req_id')
                    creqdict['req'] = {'id': req_id}

                creqlist.append(creqdict)

            # Add to response
            respdict['closed_list'] = creqlist

        return HttpResponse(json.dumps({'client': respdict}, indent=1)+'\n', content_type=json_contype)

    @allow_methods(['GET', 'POST'])
    def _openindex(request, client_id):
        if request.method == 'GET':
            return _getindex(request, client_id, listopen=True)

        elif request.method == 'POST':
            # Check/get user
            username = getusername(request)

            # Check args
            try:
                postargs = getargsfrompost(
                    request,
                    fieldnames=('action', 'req_id', 'priority', 'date_tgt', 'status', 'reason'),
                    required={'action', 'req_id'},
                    asint={'priority'}
                )
            except ValueError as e:
                return badrequest(request, e)

            # Check action
            action = postargs.pop('action').lower()
            req_id = postargs.pop('req_id')

            if action == 'open':
                # Check req_id
                if not FeatureReq.objects.filter(id=req_id).exists():
                    return badrequest(request, 'No request with id {0}'.format(req_id), 'req_id')

                # Remove unsupported args
                for fn in postargs:
                    if fn not in {'priority', 'date_tgt'}:
                        del postargs[fn]

                # Put req_id back in dict under new name
                # attachreq() takes client instead of req_id
                postargs['request'] = req_id

                # Add username and req_id
                postargs['client'] = client_id
                postargs['user'] = username

                # Now attempt to attach
                try:
                    OpenReq.objects.attachreq(**postargs)
                except Exception as e:
                    return badrequest(request, e)

                # Made it this far, good to go
                # Return updated view
                return _getindex(request, client_id, listopen=True)

            elif action == 'update':
                # Check req_id is in open list for this client
                try:
                    oreq = OpenReq.objects.get(client_id=client_id, req_id=req_id)
                except ObjectDoesNotExist:
                    return badrequest(request, 'Request not open for req_id {0}'.format(req_id), 'req_id')

                # Remove unsupported args
                for fn in postargs:
                    if fn not in {'priority', 'date_tgt'}:
                        del postargs[fn]

                # Add openreq
                postargs['openreq'] = oreq

                # Now attempt to update
                try:
                    OpenReq.objects.updatereq(**postargs)
                except Exception as e:
                    return badrequest(request, e)

                # Made it this far, good to go
                # Return updated view
                return _getindex(request, client_id, listopen=True)

            elif action == 'close':
                # Check req_id is in open list for this client
                try:
                    oreq = OpenReq.objects.get(client_id=client_id, req_id=req_id)
                except ObjectDoesNotExist:
                    return badrequest(request, 'Request not open for req_id {0}'.format(req_id), 'req_id')

                # Remove unsupported args
                for fn in postargs:
                    if fn not in {'status', 'reason'}:
                        del postargs[fn]

                # Put client_id back in dict under new name
                # closereq() takes client instead of client_id
                postargs['client'] = client_id

                # Add username and openreq
                postargs['request'] = oreq
                postargs['user'] = username

                # Now attempt to close
                try:
                    ClosedReq.objects.closereq(**postargs)
                except Exception as e:
                    return badrequest(request, e)

                # Made it this far, good to go
                # Return updated view
                return _getindex(request, client_id, listopen=True)

            else:
                return badrequest(request, 'Invalid action "{0}"'.format(action), field='action')

    @allow_methods(['GET'])
    def _closedindex(request, client_id):
        if request.method == 'GET':
            return _getindex(request, client_id, listclosed=True)
        # TODO: handle POST(?)

    @allow_methods(['GET'])
    def _allindex(request, client_id):
        return _getindex(request, client_id, listopen=True, listclosed=True)

    # Check if client_id exists
    if not ClientInfo.objects.filter(id=client_id).exists():
        return HttpResponseNotFound(json404str, content_type=json_contype)
    else:
        if tolist == 'open':
            return _openindex(request, client_id)
        elif tolist == 'closed':
            return _closedindex(request, client_id)
        elif tolist == 'all':
            return _allindex(request, client_id)

