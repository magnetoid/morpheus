from django.urls import path

from plugins.installed.promotions import views

app_name = 'promotions'

urlpatterns = [
    path('', views.promotions_index, name='index'),
]
