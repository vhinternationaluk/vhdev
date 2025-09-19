# payments/views.py

import razorpay
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Payment
from order_management.models import Order
from .serializers import PaymentSerializer,CreateOrderSerializer
# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET_KEY)
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    """
    Creates a Razorpay order and a corresponding Payment record in the database.
    """
    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    order_id = serializer.validated_data['order_id']
    amount = serializer.validated_data['amount']
    user = request.user

    try:
        order = Order.objects.get(id=order_id, user=user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    # Razorpay expects the amount in paise (or the smallest currency unit)
    amount_in_paise = int(amount * 100)

    # Create Razorpay order
    razorpay_order = razorpay_client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": str(order_id),
        "notes": {"user_id": str(user.id)}
    })

    # Create a payment record in your database
    payment = Payment.objects.create(
        order=order,
        user=user,
        amount=amount,
        razorpay_order_id=razorpay_order['id']
    )

    return Response({
        "razorpay_order_id": razorpay_order['id'],
        "razorpay_key": settings.RAZORPAY_API_KEY,
        "amount": amount_in_paise,
        "currency": "INR",
        "payment_id": payment.id
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def verify_payment(request):
    """
    Verifies the payment signature returned by Razorpay frontend.
    This should be called after the user completes the payment.
    """
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature = request.data.get('razorpay_signature')

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
        razorpay_client.utility.verify_payment_signature(params_dict)

        # Signature is valid, update payment status
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.status = Payment.PaymentStatus.CAPTURED
        payment.save()
        
        # Also update the main order status
        payment.order.is_paid = True
        payment.order.save()

        return Response({"status": "Payment successful"}, status=status.HTTP_200_OK)

    except Payment.DoesNotExist:
        return Response({"error": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated]) # Should be admin-only in production
def capture_payment(request):
    """Manually capture a payment that was only authorized."""
    payment_id = request.data.get('razorpay_payment_id')
    amount = int(float(request.data.get('amount')) * 100) # Amount in paise

    try:
        capture_data = razorpay_client.payment.capture(payment_id, amount)
        # Update your database accordingly
        payment = Payment.objects.get(razorpay_payment_id=payment_id)
        payment.status = Payment.PaymentStatus.CAPTURED
        payment.save()
        return Response(capture_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated]) # Should be admin-only in production
def refund_payment(request, paymentId):
    """Initiate a full or partial refund for a captured payment."""
    try:
        payment = Payment.objects.get(id=paymentId)
        if payment.status != Payment.PaymentStatus.CAPTURED:
            return Response({"error": "Only captured payments can be refunded."}, status=status.HTTP_400_BAD_REQUEST)

        refund_data = razorpay_client.payment.refund(payment.razorpay_payment_id, {"amount": int(payment.amount * 100)})
        
        payment.status = Payment.PaymentStatus.REFUNDED
        payment.save()

        return Response(refund_data, status=status.HTTP_200_OK)
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_status(request, paymentId):
    """Get the status of a specific payment."""
    try:
        payment = Payment.objects.get(id=paymentId, user=request.user)
        razorpay_payment = razorpay_client.payment.fetch(payment.razorpay_payment_id)
        return Response(razorpay_payment, status=status.HTTP_200_OK)
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
