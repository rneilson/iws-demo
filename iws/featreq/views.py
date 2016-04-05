import datetime, json
from collections import OrderedDict
from django.http import HttpResponse, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from .models import FeatureReq, ClientInfo, OpenReq, ClosedReq, approxnow, tojsondict, qset_vals_tojsonlist

# Default 404 JSON response dict
# Views may add extra information, or JSONify and send as-is
json404 = OrderedDict([('error', 'Resource not found')])
json404str = json.dumps(json404, indent=1) + '\n'

def index(request):
    return HttpResponse('Uh, hi?\n')

def reqindex(request):
    # TODO: add filter options, additional field options
    # Get JSON-compat dicts for all featreqs
    # (We only get fields id and title here, for brevity)
    frlist = qset_vals_tojsonlist(FeatureReq.objects, ('id', 'title'))
    # Construct response
    respdict = OrderedDict([('req_count', len(frlist)), ('req_list', frlist)])
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def reqbyid(request, req_id):
    # Get selected featreq
    try:
        fr = FeatureReq.objects.get(id=req_id)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(json404str, content_type='application/json')
    else:
        # Return (ordered) dict as JSON
        return HttpResponse(json.dumps(fr.jsondict(), indent=1)+'\n', content_type='application/json')

def clientindex(request):
    # TODO: add filter options, additional field options
    # Get JSON-compat dicts for all clients
    # (We only get fields id and name here, for brevity)
    cllist = qset_vals_tojsonlist(ClientInfo.objects, ('id', 'name'))
    # Construct response
    respdict = OrderedDict([('client_count', len(cllist)), ('client_list', cllist)])
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def clientbyid(request, client_id):
    # Get selected featreq
    try:
        cl = ClientInfo.objects.get(id=client_id)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(json404str, content_type='application/json')
    else:
        # Return (ordered) dict as JSON
        return HttpResponse(json.dumps(cl.jsondict(), indent=1)+'\n', content_type='application/json')

def openindex(request):
    # TODO: add filter options, additional field options
    # Get QuerySet of clients, with number of open requests
    oreqbycl = OpenReq.objects.values("client_id").annotate(open_count=Count('client_id'))
    # Convert to JSON-compat list (with translators)
    oreqlist = qset_vals_tojsonlist(oreqbycl, ('client_id', 'open_count'), (OpenReq.fields['client_id'], None))
    # Return list as JSON
    respdict = OrderedDict([
        ('open_client_count', len(oreqlist)),
        ('open_client_list', oreqlist)
    ])
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def openbyclient(request, client_id):
    # TODO: add filter options, additional field options
    # TODO: check if client_id exists first
    # Copy fields dict and strip out unwanted fields
    tmpfields = OpenReq.fields.copy()
    del tmpfields['client_id']
    del tmpfields['req_id']
    # Add req field and (re)use tojsondict() as translator
    tmpfields['req'] = tojsondict
    # Get open reqs for client, add JSON-compat dict to list
    oreqlist = []
    for oreq in OpenReq.objects.filter(client_id=client_id).select_related('req'):
        oreqlist.append(oreq.jsondict(fields=tmpfields.keys(), fcalls=tmpfields.values()))
    # Construct response
    respdict = OrderedDict([
        ('client_id', client_id),
        ('open_req_count', len(oreqlist)),
        ('open_req_list', oreqlist)
    ])
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def closedindex(request):
    # TODO: add filter options, additional field options
    # Get QuerySet of clients, with number of open requests
    oreqbycl = ClosedReq.objects.values("client_id").annotate(closed_count=Count('client_id'))
    # Convert to JSON-compat list (with translators)
    oreqlist = qset_vals_tojsonlist(oreqbycl, ('client_id', 'closed_count'), (ClosedReq.fields['client_id'], None))
    # Return list as JSON
    respdict = OrderedDict([
        ('closed_client_count', len(oreqlist)),
        ('closed_client_list', oreqlist)
    ])
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def closedbyclient(request, client_id):
    # TODO: add filter options, additional field options
    # TODO: check if client_id exists first
    # Copy fields dict and strip out unwanted fields
    tmpfields = ClosedReq.fields.copy()
    del tmpfields['client_id']
    del tmpfields['req_id']
    # Add req field and (re)use tojsondict() as translator
    tmpfields['req'] = tojsondict
    # Get closed reqs for client, add JSON-compat dict to list
    oreqlist = []
    for oreq in ClosedReq.objects.filter(client_id=client_id).select_related('req'):
        oreqlist.append(oreq.jsondict(fields=tmpfields.keys(), fcalls=tmpfields.values()))
    # Construct response
    respdict = OrderedDict([
        ('client_id', client_id),
        ('closed_req_count', len(oreqlist)),
        ('closed_req_list', oreqlist)
    ])
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')


