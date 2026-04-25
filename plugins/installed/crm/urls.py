from django.urls import path

from plugins.installed.crm import views

app_name = 'crm'

urlpatterns = [
    path('', views.crm_home, name='home'),
    path('leads/', views.leads_list, name='leads'),
    path('pipeline/', views.pipeline_board, name='pipeline'),
    path('tasks/', views.tasks_list, name='tasks'),
]
