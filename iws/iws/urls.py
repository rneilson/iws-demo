"""iws URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.conf import settings

urlpatterns = [
    url(r'^featreq/', include('featreq.urls')),
]

# Enable admin only if set
if hasattr(settings, 'IWS_ENABLE_ADMIN') and settings.IWS_ENABLE_ADMIN:
    from django.contrib import admin
    admin.site.site_header = 'IWS-Demo administration'
    admin.site.site_title = 'IWS-Demo site admin'
    urlpatterns.append(url(r'^admin/', admin.site.urls))
    
