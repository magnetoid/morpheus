from django.urls import path

from plugins.installed.draft_orders import views

app_name = 'draft_orders'

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:number>/', views.detail, name='detail'),
    path('<str:number>/convert/', views.convert, name='convert'),
]
