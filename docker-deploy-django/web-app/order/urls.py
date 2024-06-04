from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('product-catalog/', views.product_catalog, name='product_catalog'),
    path('order-product/<int:product_id>/', views.order_product, name='order_product'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('track-order-form/', views.track_order_form, name='track_order_form'),
    path('track-order/', views.track_order, name='track_order'),
    path('order_list/', views.order_list, name='order_list'),
]