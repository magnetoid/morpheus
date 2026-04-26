from django.urls import path

from plugins.installed.demo_data import views

app_name = 'demo_data'

urlpatterns = [
    path('settings/', views.demo_data_index, name='settings'),
    path('index/', views.demo_data_index, name='index'),
]
