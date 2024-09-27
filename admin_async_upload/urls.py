from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^upload/$', views.admin_resumable, name='admin_resumable'),
]
