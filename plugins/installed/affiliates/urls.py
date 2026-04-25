from __future__ import annotations

from django.urls import path

from plugins.installed.affiliates.views import affiliate_redirect

app_name = 'affiliates'

urlpatterns = [
    path('r/<str:code>', affiliate_redirect, name='redirect'),
]
