try:
    from django.urls import re_path, include
except ImportError:
    from django.conf.urls import url as re_path, include
import appmail.urls
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^appmail/", include(appmail.urls)),
]
