try:
    from django.urls import include, re_path
except ImportError:
    from django.conf.urls import url as re_path, include

from django.contrib import admin

import appmail.urls

admin.autodiscover()

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^appmail/", include(appmail.urls)),
]
