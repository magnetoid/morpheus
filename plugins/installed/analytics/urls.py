from django.urls import path

from plugins.installed.analytics import views

app_name = 'analytics'

api_urlpatterns = [
    path('analytics/track/', views.track_beacon, name='track'),
    path('analytics/realtime.json', views.realtime_json, name='realtime_json'),
]

dashboard_urlpatterns = [
    path('', views.overview, name='overview'),
    path('realtime/', views.realtime, name='realtime'),
    path('funnel/', views.funnel_view, name='funnel'),
]
