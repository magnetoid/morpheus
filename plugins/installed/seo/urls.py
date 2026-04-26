from django.urls import path

from plugins.installed.seo import views

app_name = 'seo'

urlpatterns = [
    path('sitemap.xml', views.sitemap_xml, name='sitemap'),
    path('robots.txt', views.robots_txt, name='robots'),
    path('llms.txt', views.llms_txt, name='llms_txt'),
    path('llms-full.txt', views.llms_full_txt, name='llms_full_txt'),
    path('ai/products.json', views.ai_products_feed, name='ai_feed'),
]
