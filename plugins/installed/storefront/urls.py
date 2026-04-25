from django.urls import path
from plugins.installed.storefront import views

app_name = 'storefront'
urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('search/', views.search, name='search'),

    # Content / static
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('journal/', views.journal_index, name='journal_index'),
    path('journal/<slug:slug>/', views.journal_detail, name='journal_detail'),
    path('categories/', views.categories, name='categories'),

    # Customer account
    path('account/', views.account_home, name='account_home'),
    path('account/orders/', views.account_orders, name='account_orders'),
    path('account/orders/<str:order_number>/', views.account_order_detail, name='account_order_detail'),

    # Order confirmation (post-checkout)
    path('order/confirmation/<str:order_number>/', views.order_confirmation, name='order_confirmation'),

    # Generic placeholder pages (footer links without first-class content yet)
    path('stockists/', views.coming_soon, {'slug': 'stockists'}, name='stockists'),
    path('staff-picks/', views.coming_soon, {'slug': 'staff-picks'}, name='staff_picks'),
    path('shipping/', views.coming_soon, {'slug': 'shipping'}, name='shipping'),
    path('returns/', views.coming_soon, {'slug': 'returns'}, name='returns'),
]
