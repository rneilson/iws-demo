import datetime, json
from collections import OrderedDict
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import FeatureReq, ClientInfo, OpenReq, ClosedReq, approxnow, qset_vals_tojsonlist

def index(request):
    return HttpResponse('Uh, hi?\n')

def reqindex(request):
    # TODO: add filter options, additional field options
    # Get JSON-compat dicts for all featreqs
    # (Only get fields id and title)
    frlist = qset_vals_tojsonlist(FeatureReq.objects, 'id', 'title')
    # Construct response
    respdict = OrderedDict([('req-count', len(frlist)), ('req-list', frlist)])
    #return JsonResponse(respdict, json_dumps_params={'indent':1})
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def reqbyid(request, req_id):
    # Get selected featreq
    fr = FeatureReq.objects.get(id=req_id)
    # Return (ordered) dict as JSON
    return HttpResponse(json.dumps(fr.jsondict(), indent=1)+'\n', content_type='application/json')

def clientindex(request):
    # TODO: add filter options, additional field options
    # Get JSON-compat dicts for all clients
    # (Only get fields id and name)
    cllist = qset_vals_tojsonlist(ClientInfo.objects, 'id', 'name')
    # Construct response
    respdict = OrderedDict([('client-count', len(cllist)), ('client-list', cllist)])
    #return JsonResponse(respdict, json_dumps_params={'indent':1})
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def clientbyid(request, client_id):
    # Get selected featreq
    cl = ClientInfo.objects.get(id=client_id)
    # Return (ordered) dict as JSON
    return HttpResponse(json.dumps(cl.jsondict(), indent=1)+'\n', content_type='application/json')

def openindex(request):
    # TODO: add filter options, additional field options
    # Get JSON-compat dicts for all open reqs
    oreqlist = qset_vals_tojsonlist(OpenReq.objects, 'client_id', 'req_id', 'priority', 'opened_at')
    # Construct response
    respdict = OrderedDict()
    respdict['open-req-list'] = oreqlist
    #return JsonResponse(respdict, json_dumps_params={'indent':1})
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def closedindex(request):
    # TODO: add filter options, additional field options
    # Get JSON-compat dicts for all closed reqs
    creqlist = qset_vals_tojsonlist(OpenReq.objects, 'client_id', 'req_id', 'priority', 'closed_at')
    # Construct response
    respdict = OrderedDict()
    respdict['closed-req-list'] = creqlist
    #return JsonResponse(respdict, json_dumps_params={'indent':1})
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

