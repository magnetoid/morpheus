from django.urls import path

from plugins.installed.admin_dashboard import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('orders/', views.orders_list, name='orders'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('products/', views.products_list, name='products'),
    path('customers/', views.customers_list, name='customers'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('marketing/', views.marketing_view, name='marketing'),
    path('apps/', views.apps_view, name='apps'),
    path('settings/', views.settings_view, name='settings'),
    path('ai-insights/', views.ai_insights, name='ai_insights'),
]
