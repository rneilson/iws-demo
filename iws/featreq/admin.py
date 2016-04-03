from django.contrib import admin
from .models import FeatureReq, ClientInfo, OpenReq, ClosedReq

admin.site.register(FeatureReq)
admin.site.register(ClientInfo)
admin.site.register(OpenReq)
admin.site.register(ClosedReq)
