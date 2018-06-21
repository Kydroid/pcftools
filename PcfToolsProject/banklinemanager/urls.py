from django.conf.urls import url

from . import views

app_name='banklinemanager'


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^import-data/$', views.import_data, name='import_data'),
    url(r'^search/$', views.search, name='search'),
    #url(r'^(?P<album_id>[0-9]+)/$', views.detail, name='detail'),
]