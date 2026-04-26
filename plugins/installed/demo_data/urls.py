from django.urls import path

from plugins.installed.demo_data import views

app_name = 'demo_data'

urlpatterns = [
    path('settings/', views.settings_view, name='settings'),
]
