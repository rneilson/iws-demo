import datetime, json
from collections import OrderedDict
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import FeatureReq, ClientInfo, OpenReq, ClosedReq, approxnow

def index(request):
    return HttpResponse('Uh, hi?\n')

def reqindex(request):
    # TODO: add filter options
    # Get JSON-compat dicts for all featreqs
    frlist = [ fr.jsondict() for fr in FeatureReq.objects.all() ]
    # Construct response
    respdict = OrderedDict()
    respdict['req-list'] = frlist
    #return JsonResponse(respdict, json_dumps_params={'indent':1})
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def reqbyid(request, req_id):
    # Get selected featreq
    fr = FeatureReq.objects.get(id=req_id)
    # Return (ordered) dict as JSON
    return HttpResponse(json.dumps(fr.jsondict(), indent=1)+'\n', content_type='application/json')

def clientindex(request):
    # TODO: add filter options
    # Get JSON-compat dicts for all clients
    cllist = [ cl.jsondict() for cl in ClientInfo.objects.all() ]
    # Construct response
    respdict = OrderedDict()
    respdict['client-list'] = cllist
    #return JsonResponse(respdict, json_dumps_params={'indent':1})
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def clientbyid(request, client_id):
    # Get selected featreq
    cl = ClientInfo.objects.get(id=client_id)
    # Return (ordered) dict as JSON
    return HttpResponse(json.dumps(cl.jsondict(), indent=1)+'\n', content_type='application/json')

def openindex(request):
    # TODO: add filter options
    # Get JSON-compat dicts for all open reqs
    oreqlist = [ oreq.jsondict() for oreq in OpenReq.objects.all() ]
    # Construct response
    respdict = OrderedDict()
    respdict['open-req-list'] = oreqlist
    #return JsonResponse(respdict, json_dumps_params={'indent':1})
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

def closedindex(request):
    # TODO: add filter options
    # Get JSON-compat dicts for all closed reqs
    creqlist = [ creq.jsondict() for creq in ClosedReq.objects.all() ]
    # Construct response
    respdict = OrderedDict()
    respdict['closed-req-list'] = creqlist
    #return JsonResponse(respdict, json_dumps_params={'indent':1})
    return HttpResponse(json.dumps(respdict, indent=1)+'\n', content_type='application/json')

