from django.urls import path
from plugins.installed.admin_dashboard import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('products/', views.products_list, name='products'),
    path('orders/', views.orders_list, name='orders'),
    path('customers/', views.customers_list, name='customers'),
    path('ai-insights/', views.ai_insights, name='ai_insights'),
]
