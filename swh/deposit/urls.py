# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""SWH's main deposit URL Configuration

"""

from django.conf.urls import url, include
from django.shortcuts import render
from django.views.generic.base import RedirectView
from rest_framework.urlpatterns import format_suffix_patterns

favicon_view = RedirectView.as_view(
    url="/static/img/icons/swh-logo-32x32.png", permanent=True
)


def default_view(req):
    return render(req, "homepage.html")


urlpatterns = [
    url(r"^favicon\.ico$", favicon_view),
    url(r"^1/", include("swh.deposit.api.urls")),
    url(r"^1/private/", include("swh.deposit.api.private.urls")),
    url(r"^$", default_view, name="home"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
