# urls.py
from django.urls import path
from .views import (
    OrderCreateView,
    OrderListView, 
    OrderDetailView,
    cancel_order,
    track_order,
    return_order,
    update_payment
)

urlpatterns = [
    # POST /api/orders - Create a new order
    path('', OrderCreateView.as_view(), name='order-create'),
    
    # GET /api/orders - List all orders for the user
    path('', OrderListView.as_view(), name='order-list'),
    
    # GET /api/{orderId} - Get specific order details
    # PUT /api/{orderId} - Update order details
    path('<uuid:orderId>/', OrderDetailView.as_view(), name='order-detail'),
    
    # PUT /api/{orderId}/payment - Update payment details
    path('<uuid:orderId>/payment/', update_payment, name='order-payment-update'),
    
    # PUT /api/{orderId}/cancel - Cancel an order
    path('<uuid:orderId>/cancel/', cancel_order, name='order-cancel'),
    
    # GET /api/{orderId}/track - Track order status
    path('<uuid:orderId>/track/', track_order, name='order-track'),
    
    # POST /api/{orderId}/return - Return an order
    path('<uuid:orderId>/return/', return_order, name='order-return'),
]

# Note: You need to include these URLs in your main urls.py:
# 
# from django.urls import path, include
# 
# urlpatterns = [
#     path('api/', include('your_orders_app.urls')),
# ]