from django.urls import path
from . import views

urlpatterns = [
    path('api/payments/create-order', views.create_order, name='create-order'),
    path('api/payments/verify', views.verify_payment, name='verify-payment'),
    path('api/payments/capture', views.capture_payment, name='capture-payment'),
    path('api/payments/<uuid:paymentId>/refund', views.refund_payment, name='refund-payment'),
    path('api/payments/<uuid:paymentId>/status', views.get_payment_status, name='payment-status'),
]