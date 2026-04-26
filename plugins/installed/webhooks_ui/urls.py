from django.urls import path

from plugins.installed.webhooks_ui import views

app_name = 'webhooks_ui'

urlpatterns = [
    path('', views.endpoints_list, name='endpoints_list'),
    path('new/', views.endpoint_create, name='endpoint_create'),
    path('<uuid:endpoint_id>/edit/', views.endpoint_edit, name='endpoint_edit'),
    path('<uuid:endpoint_id>/delete/', views.endpoint_delete, name='endpoint_delete'),
    path('deliveries/', views.deliveries_list, name='deliveries_list'),
    path('deliveries/<uuid:delivery_id>/replay/', views.delivery_replay, name='delivery_replay'),
]
