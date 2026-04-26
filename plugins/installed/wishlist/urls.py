from django.urls import path

from plugins.installed.wishlist import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist_view, name='home'),
    path('add/', views.add_to_wishlist_view, name='add'),
    path('remove/<uuid:item_id>/', views.remove_from_wishlist_view, name='remove'),
    path('share/', views.share_wishlist_view, name='share'),
    path('shared/<str:token>/', views.shared_wishlist_view, name='shared'),
]
