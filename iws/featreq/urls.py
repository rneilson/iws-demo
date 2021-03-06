from django.conf.urls import url, include
from . import views

req_patterns = [
    url(r'^$', views.reqindex, name='featreq-req-index'),
    url(r'^(?P<tolist>open|closed|all)/$', views.reqindex_ext, name='featreq-req-index-ext'),
    url(r'^(?i)(?P<req_id>[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12})', include([
        url(r'^$', views.reqbyid, name='featreq-req-byid'),
        url(r'^/(?P<tolist>open|closed|all)/$', views.reqbyid_ext, name='featreq-req-byid-ext'),
        url(r'^/$', views.reqredir)
    ]))
]

client_patterns = [
    url(r'^$', views.clientindex, name='featreq-client-index'),
    url(r'^(?i)(?P<client_id>[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12})', include([
        url(r'^$', views.clientbyid, name='featreq-client-byid'),
        url(r'^/(?P<tolist>open|closed|all)/$', views.clientreqindex, name='featreq-client-index-ext'),
        url(r'^/$', views.clientredir)
    ]))
]

urlpatterns = [
    url(r'^$', views.index, name='featreq-index'),
    url(r'^login/', views.weblogin, name='featreq-login'),
    url(r'^auth/', views.apiauth, name='featreq-auth'),
    url(r'^req/', include(req_patterns)),
    url(r'^client/', include(client_patterns)),
]

    # url(r'^open/$', views.openindexbyclient, name='featreq-open-index'),
    # url(r'^closed/$', views.closedindexbyclient, name='featreq-closed-index'),
    # url(r'^open/(?i)(?P<client_id>[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12})/$', 
    #     views.openbyclient, name='featreq-open-byclient'),
    # url(r'^closed/(?i)(?P<client_id>[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12})/$', 
    #     views.closedbyclient, name='featreq-closed-byclient'),
