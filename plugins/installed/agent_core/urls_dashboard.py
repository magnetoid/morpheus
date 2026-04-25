"""Admin dashboard routes mounted under `/dashboard/agents/`."""
from __future__ import annotations

from django.urls import path

from plugins.installed.agent_core import views

app_name = 'agent_core_dash'

urlpatterns = [
    path('', views.runs_dashboard_view, name='runs'),
    path('console/', views.merchant_ops_chat_view, name='console'),
    path('<uuid:run_id>/', views.run_detail_view, name='run_detail'),
]
