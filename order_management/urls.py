# orders/urls.py

from django.urls import path
from .views import (
    OrderCreateView, OrderListView, OrderDetailView,AdminOrderStatusUpdateView,
    update_payment, cancel_order, track_order, return_order
)

urlpatterns = [
    # Separate POST for creation and GET for listing
    path('', OrderListView.as_view(), name='order-list'),
    path('create/', OrderCreateView.as_view(), name='order-create'),
    
    # Order-specific actions
    path('<uuid:orderId>/', OrderDetailView.as_view(), name='order-detail'),
    path('<uuid:orderId>/payment/', update_payment, name='order-payment-update'),
    path('<uuid:orderId>/cancel/', cancel_order, name='order-cancel'),
    path('<uuid:orderId>/track/', track_order, name='order-track'),
    path('<uuid:orderId>/return/', return_order, name='order-return'),
    path('<uuid:orderId>/status/', AdminOrderStatusUpdateView.as_view(), name='admin-order-status-update'),

]
