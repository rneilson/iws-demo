import datetime, json
from collections import OrderedDict
from functools import partial
from django.http import HttpResponse, HttpResponseNotFound, HttpResponsePermanentRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse as urlreverse
from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from .models import FeatureReq, ClientInfo, OpenReq, ClosedReq
from .utils import approxnow, tojsondict, qset_vals_tojsonlist

# Default 404 JSON response dict
# Views may add extra information, or JSONify and send as-is
json404 = OrderedDict([('error', 'Resource not found')])
json404str = json.dumps(json404, indent=1) + '\n'
json_contype = 'application/json'

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
del openreq_byclient_fields['req_id']
openreq_byclient_fields['req'] = tojsondict

closedreq_byclient_fields = ClosedReq.fields.copy()
del closedreq_byclient_fields['client_id']
del closedreq_byclient_fields['req_id']
closedreq_byclient_fields['req'] = tojsondict

## Views

def index(request):
    return HttpResponse('Uh, hi?\n')

def reqindex(request, tolist=''):
    # TODO: add filter options, additional field options
    # Get JSON-compat dicts for all featreqs
    if not tolist:
        # We only get fields id and title here, for brevity
        frlist = qset_vals_tojsonlist(FeatureReq.objects, ('id', 'title'))
    else:
        if tolist == 'open':
            listopen = True
            listclosed = False
        elif tolist == 'closed':
            listopen = False
            listclosed = True
        elif tolist == 'all':
            listopen = True
            listclosed = True

        # We'll feed each FeatureReq into an OrderedDict by id, and append matching
        # OpenReqs to them
        frdict = OrderedDict()

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
                    fr = oreq.req.jsondict()
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
                    fr = creq.req.jsondict()
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

def reqbyid(request, req_id):
    # Get selected featreq
    try:
        fr = FeatureReq.objects.get(id=req_id)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(json404str, content_type=json_contype)
    else:
        # Return (ordered) dict as JSON
        return HttpResponse(json.dumps(fr.jsondict(), indent=1)+'\n', content_type=json_contype)

def reqredir(request, req_id):
    # Check if req_id exists
    if FeatureReq.objects.filter(id=req_id).exists():
        # Redirect to proper featreq URL
        return HttpResponsePermanentRedirect(urlreverse('featreq-req-byid', args=(req_id,)))
    else:
        return HttpResponseNotFound(json404str, content_type=json_contype)

def clientindex(request, tolist=''):
    # TODO: add filter options, additional field options
    # Get JSON-compat dicts for all clients
    # Get client id, name, and open/closed counts
    clqset = ClientInfo.objects.annotate(
        open_count=Count('open_list', distinct=True), 
        closed_count=Count('closed_list', distinct=True))
    cllist = qset_vals_tojsonlist(clqset, client_with_counts_dict.keys(), client_with_counts_dict.values())
    # Construct response
    respdict = OrderedDict([('client_count', len(cllist)), ('client_list', cllist)])
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type=json_contype)

def clientbyid(request, client_id):
    # Get selected featreq
    try:
        cl = ClientInfo.objects.get(id=client_id)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(json404str, content_type=json_contype)
    else:
        # Return (ordered) dict as JSON
        return HttpResponse(json.dumps(cl.jsondict(), indent=1)+'\n', content_type=json_contype)

def clientredir(request, client_id):
    # Check if client_id exists
    if ClientInfo.objects.filter(id=client_id).exists():
        # Redirect to proper featreq URL
        return HttpResponsePermanentRedirect(urlreverse('featreq-client-byid', args=(client_id,)))
    else:
        return HttpResponseNotFound(json404str, content_type=json_contype)

def clientreqindex(request, client_id, tolist):
    # Check if client_id exists
    if not ClientInfo.objects.filter(id=client_id).exists():
        return HttpResponseNotFound(json404str, content_type=json_contype)
    else:
        respdict = OrderedDict([('client_id', client_id)])

        # Get open, if requested
        if tolist == 'open' or tolist == 'all':
            # Get open reqs for client, add JSON-compat dict to list
            oreqlist = []
            for oreq in OpenReq.objects.filter(client_id=client_id).select_related('req'):
                oreqlist.append(oreq.jsondict(
                    fields=openreq_byclient_fields.keys(), 
                    fcalls=openreq_byclient_fields.values()))
            # Add to response
            respdict['open_count'] = len(oreqlist)
            respdict['open_list'] = oreqlist

        # Get closed, if requested
        if tolist == 'closed' or tolist == 'all':
            # Get closed reqs for client, add JSON-compat dict to list
            creqlist = []
            for creq in ClosedReq.objects.filter(client_id=client_id).select_related('req'):
                creqlist.append(creq.jsondict(
                    fields=closedreq_byclient_fields.keys(), 
                    fcalls=closedreq_byclient_fields.values()))
            # Add to response
            respdict['open_count'] = len(creqlist)
            respdict['open_list'] = creqlist

        return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type=json_contype)


