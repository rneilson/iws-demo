from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='featreq-index'),
    url(r'^req/$', views.reqindex, name='featreq-req-index'),
    url(r'^req/(?i)(?P<req_id>[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12})$', 
        views.reqbyid, name='featreq-req-byid'),
    url(r'^client/$', views.clientindex, name='featreq-client-index'),
    url(r'^client/(?i)(?P<client_id>[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12})$', 
        views.clientbyid, name='featreq-client-byid'),
    url(r'^open/$', views.openindex, name='featreq-open-index'),
    url(r'^closed/$', views.closedindex, name='featreq-closed-index'),
]


#   url(r'^req/(?i)(?P<req_id>[a-fA-F0-9]{8}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{12})$', 
