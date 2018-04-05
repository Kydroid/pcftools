from django.conf.urls import url

from . import views

app_name='banklinemanager'


urlpatterns = [
    url(r'^$', views.listing, name='listing'),
    #url(r'^(?P<album_id>[0-9]+)/$', views.detail, name='detail'),
    #url(r'^search/$', views.search, name='search'),
]