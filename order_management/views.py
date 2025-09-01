# orders/views.py

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer, OrderStatusUpdateSerializer
from .permissions import IsOwner,IsAdminOrSuperUser


class AdminOrderStatusUpdateView(generics.UpdateAPIView):
    """
    An admin-only endpoint to update the status of any order.
    """
    queryset = Order.objects.all()
    serializer_class = OrderStatusUpdateSerializer
    permission_classes = [IsAdminOrSuperUser] # This locks the endpoint to admins
    lookup_field = 'id'
    lookup_url_kwarg = 'orderId'

# POST /api/orders/ - Create an order
class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]

# GET /api/orders - List all orders for the user
class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Automatically filters queryset for the authenticated user from the JWT
        return Order.objects.filter(user=self.request.user)

# GET /{orderId}, PUT /{orderId}
class OrderDetailView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    lookup_field = 'id'
    lookup_url_kwarg = 'orderId'

# PUT /{orderId}/payment
@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsOwner])
def update_payment(request, orderId):
    try:
        order = Order.objects.get(id=orderId, user=request.user)
    except Order.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    order.is_paid = True
    order.save()
    return Response(OrderSerializer(order).data)

# PUT /{orderId}/cancel
@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsOwner])
def cancel_order(request, orderId):
    try:
        order = Order.objects.get(id=orderId, user=request.user)
    except Order.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if order.status not in [Order.OrderStatus.DELIVERED, Order.OrderStatus.CANCELED]:
        order.status = Order.OrderStatus.CANCELED
        order.save()
        return Response(OrderSerializer(order).data)
    else:
        return Response({"error": "This order cannot be canceled."}, status=status.HTTP_400_BAD_REQUEST)

# GET /{orderId}/track
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsOwner])
def track_order(request, orderId):
    try:
        order = Order.objects.get(id=orderId, user=request.user)
    except Order.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    return Response({"status": order.status, "updated_at": order.updated_at})

# POST /{orderId}/return
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOwner])
def return_order(request, orderId):
    try:
        order = Order.objects.get(id=orderId, user=request.user)
    except Order.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if order.status == Order.OrderStatus.DELIVERED:
        order.status = Order.OrderStatus.RETURNED
        order.save()
        return Response(OrderSerializer(order).data)
    else:
        return Response({"error": "Only delivered orders can be returned."}, status=status.HTTP_400_BAD_REQUEST)
