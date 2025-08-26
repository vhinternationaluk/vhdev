from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Order
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderTrackingSerializer, 
    OrderReturnSerializer
)


class OrderCreateView(generics.CreateAPIView):
    """
    POST /api/orders - Create a new order
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Automatically set the userId to the current user
        serializer.save(userId=self.request.user)


class OrderListView(generics.ListAPIView):
    """
    GET /api/orders - List all orders for the authenticated user
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(userId=self.request.user).select_related(
            'shippingAddress', 'billing', 'payment'
        ).prefetch_related('items')


class OrderDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/orders/{orderId} - Get specific order details
    PUT /api/orders/{orderId} - Update order details
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'orderId'
    lookup_url_kwarg = 'orderId'
    
    def get_queryset(self):
        return Order.objects.filter(userId=self.request.user).select_related(
            'shippingAddress', 'billing', 'payment'
        ).prefetch_related('items')


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def cancel_order(request, orderId):
    """
    PUT /api/orders/{orderId}/cancel - Cancel an order
    """
    order = get_object_or_404(
        Order, 
        orderId=orderId, 
        userId=request.user
    )
    
    # Check if order can be cancelled
    if order.status in ['delivered', 'cancelled', 'returned']:
        return Response(
            {'error': f'Order cannot be cancelled. Current status: {order.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Update order status to cancelled
    order.status = 'cancelled'
    order.save()
    
    # Update payment status if needed
    if hasattr(order, 'payment') and order.payment.status == 'completed':
        order.payment.status = 'refunded'
        order.payment.save()
    
    serializer = OrderSerializer(order)
    return Response({
        'message': 'Order cancelled successfully',
        'order': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_order(request, orderId):
    """
    GET /api/orders/{orderId}/track - Track order status
    """
    order = get_object_or_404(
        Order, 
        orderId=orderId, 
        userId=request.user
    )
    
    serializer = OrderTrackingSerializer(order)
    
    # Add tracking information
    tracking_info = {
        'order': serializer.data,
        'tracking_updates': get_tracking_updates(order)
    }
    
    return Response(tracking_info)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def return_order(request, orderId):
    """
    POST /api/orders/{orderId}/return - Return an order
    """
    order = get_object_or_404(
        Order, 
        orderId=orderId, 
        userId=request.user
    )
    
    # Check if order can be returned
    if order.status != 'delivered':
        return Response(
            {'error': 'Only delivered orders can be returned'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = OrderReturnSerializer(data=request.data)
    if serializer.is_valid():
        # Update order status to returned
        order.status = 'returned'
        order.save()
        
        # Update payment status for refund processing
        if hasattr(order, 'payment'):
            order.payment.status = 'refunded'
            order.payment.save()
        
        # Here you would typically create a Return record
        # and initiate the refund process
        
        order_serializer = OrderSerializer(order)
        return Response({
            'message': 'Return request submitted successfully',
            'reason': serializer.validated_data['reason'],
            'returnDate': timezone.now(),
            'order': order_serializer.data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_payment(request, orderId):
    """
    PUT /api/orders/{orderId}/payment - Update payment details after Razorpay response
    """
    order = get_object_or_404(
        Order, 
        orderId=orderId, 
        userId=request.user
    )
    
    # Check if payment can be updated
    if not hasattr(order, 'payment'):
        return Response(
            {'error': 'No payment information found for this order'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    payment_data = request.data
    required_fields = ['paymentId', 'status']
    
    # Validate required fields
    for field in required_fields:
        if field not in payment_data:
            return Response(
                {'error': f'{field} is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Update payment details
    payment = order.payment
    payment.paymentId = payment_data['paymentId']
    payment.status = payment_data['status']
    
    # Update method if provided
    if 'method' in payment_data:
        payment.method = payment_data['method']
    
    payment.save()
    
    # Update order status based on payment status
    if payment.status == 'completed':
        order.status = 'confirmed'
        order.save()
    elif payment.status == 'failed':
        order.status = 'cancelled'
        order.save()
    
    serializer = OrderSerializer(order)
    return Response({
        'message': 'Payment updated successfully',
        'order': serializer.data
    })
    """
    Helper function to generate tracking updates based on order status
    """
    updates = []
    
    if order.orderDate:
        updates.append({
            'status': 'Order Placed',
            'timestamp': order.orderDate,
            'description': 'Your order has been placed successfully'
        })
    
    if order.status in ['confirmed', 'shipped', 'delivered']:
        updates.append({
            'status': 'Order Confirmed',
            'timestamp': order.orderDate,  # You might want to add a confirmed_date field
            'description': 'Your order has been confirmed'
        })
    
    if order.status in ['shipped', 'delivered']:
        updates.append({
            'status': 'Order Shipped',
            'timestamp': order.orderDate,  # You might want to add a shipped_date field
            'description': 'Your order has been shipped'
        })
    
    if order.status == 'delivered' and order.deliveryDate:
        updates.append({
            'status': 'Order Delivered',
            'timestamp': order.deliveryDate,
            'description': 'Your order has been delivered'
        })
    
    if order.status == 'cancelled':
        updates.append({
            'status': 'Order Cancelled',
            'timestamp': order.updated_at,
            'description': 'Your order has been cancelled'
        })
    
    if order.status == 'returned':
        updates.append({
            'status': 'Order Returned',
            'timestamp': order.updated_at,
            'description': 'Your order has been returned'
        })
    
    return updates
