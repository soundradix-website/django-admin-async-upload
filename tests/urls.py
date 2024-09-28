import django
from django.urls import re_path
from django.contrib import admin
from django.conf import settings

import admin_async_upload.views

urlpatterns = [
    re_path(r'^admin_resumable/', admin_async_upload.views.admin_resumable, name="admin_resumable"),
    re_path(r'^admin/', admin.site.urls),
]


if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += [
        (r'^media/(?P<path>.*)$', django.views.static.serve,
            {'document_root': settings.MEDIA_ROOT})
    ]
