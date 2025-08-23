from django.urls import path
from . import views

urlpatterns = [
    # Product Category
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<uuid:pk>/', views.category_detail, name='category_detail'),
    path('categories/<uuid:pk>/update/', views.category_update, name='category_update'),
    path('categories/<uuid:pk>/delete/', views.category_delete, name='category_delete'),

    # Product
    path('list/', views.product_list, name='product_list'),  # public read
    path('<uuid:pk>/', views.product_detail, name='product_detail'),  # public read
    path('bycategoryid/<uuid:category_id>/', views.products_by_category, name='products_by_category'),  # public read

    path('create/', views.product_create, name='product_create'),
    path('<uuid:pk>/update/', views.product_update, name='product_update'),
    path('<uuid:pk>/delete/', views.product_delete, name='product_delete'),
    path('api/cart/', views.CartAPIView.as_view(), name='cart-detail'),
    path('api/cart/items/', views.add_to_cart, name='add-to-cart'),
    path('api/cart/items/<int:itemId>/', views.update_cart_item, name='update-cart-item'),
    path('api/cart/items/<int:itemId>/', views.remove_cart_item, name='remove-cart-item'),
    path('api/cart/clear/', views.clear_cart, name='clear-cart'),
    path('api/cart/summary/', views.CartSummaryAPIView.as_view(), name='cart-summary'),

]
