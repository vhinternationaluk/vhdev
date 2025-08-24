from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.utils import timezone
import razorpay
import hashlib
import hmac
import logging
from decimal import Decimal
from django.conf import settings
from .models import PaymentOrder, PaymentRefund
from .serializers import (
    CreateOrderSerializer, PaymentVerificationSerializer,
    PaymentCaptureSerializer, PaymentRefundSerializer,
    PaymentOrderResponseSerializer
)

logger = logging.getLogger(__name__)

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    """
    Create a new payment order with Razorpay
    """
    try:
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        customer_details = validated_data['customerDetails']
        
        # Get user
        try:
            user = User.objects.get(id=validated_data['userId'])
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if order ID already exists
        if PaymentOrder.objects.filter(order_id=validated_data['orderId']).exists():
            return Response({
                'success': False,
                'error': 'Order ID already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert amount to paise (Razorpay expects amount in smallest currency unit)
        amount_in_paise = int(validated_data['amount'] * 100)
        
        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            'amount': amount_in_paise,
            'currency': validated_data['currency'],
            'receipt': validated_data['orderId'],
            'notes': {
                'user_id': str(user.id),
                'order_id': validated_data['orderId']
            }
        })
        
        # Create payment order in database
        payment_order = PaymentOrder.objects.create(
            order_id=validated_data['orderId'],
            razorpay_order_id=razorpay_order['id'],
            user=user,
            amount=validated_data['amount'],
            currency=validated_data['currency'],
            customer_name=customer_details['name'],
            customer_email=customer_details['email'],
            customer_phone=customer_details['phone'],
            status='created'
        )
        
        logger.info(f"Payment order created: {payment_order.order_id}")
        
        return Response({
            'success': True,
            'data': {
                'orderId': payment_order.order_id,
                'razorpayOrderId': razorpay_order['id'],
                'amount': validated_data['amount'],
                'currency': validated_data['currency'],
                'keyId': settings.RAZORPAY_KEY_ID,
                'customerDetails': customer_details
            }
        }, status=status.HTTP_201_CREATED)
        
    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay bad request: {str(e)}")
        return Response({
            'success': False,
            'error': 'Invalid payment request',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error creating payment order: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """
    Verify payment signature from Razorpay
    """
    try:
        serializer = PaymentVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        # Get payment order
        try:
            payment_order = PaymentOrder.objects.get(
                order_id=validated_data['orderId'],
                razorpay_order_id=validated_data['razorpay_order_id']
            )
        except PaymentOrder.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify signature
        expected_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
            f"{validated_data['razorpay_order_id']}|{validated_data['razorpay_payment_id']}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if expected_signature != validated_data['razorpay_signature']:
            logger.warning(f"Invalid signature for payment: {validated_data['razorpay_payment_id']}")
            return Response({
                'success': False,
                'error': 'Invalid payment signature'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update payment order
        payment_order.razorpay_payment_id = validated_data['razorpay_payment_id']
        payment_order.razorpay_signature = validated_data['razorpay_signature']
        payment_order.status = 'paid'
        payment_order.paid_at = timezone.now()
        payment_order.save()
        
        logger.info(f"Payment verified successfully: {payment_order.order_id}")
        
        return Response({
            'success': True,
            'message': 'Payment verified successfully',
            'data': {
                'orderId': payment_order.order_id,
                'paymentId': validated_data['razorpay_payment_id'],
                'status': 'paid'
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def capture_payment(request):
    """
    Capture authorized payment
    """
    try:
        serializer = PaymentCaptureSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        # Get payment order
        try:
            payment_order = PaymentOrder.objects.get(
                order_id=validated_data['orderId'],
                razorpay_payment_id=validated_data['razorpay_payment_id']
            )
        except PaymentOrder.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Convert amount to paise
        amount_in_paise = int(validated_data['amount'] * 100)
        
        # Capture payment via Razorpay
        captured_payment = razorpay_client.payment.capture(
            validated_data['razorpay_payment_id'],
            amount_in_paise
        )
        
        # Update payment order status
        payment_order.status = 'paid'
        payment_order.paid_at = timezone.now()
        payment_order.save()
        
        logger.info(f"Payment captured successfully: {payment_order.order_id}")
        
        return Response({
            'success': True,
            'message': 'Payment captured successfully',
            'data': {
                'orderId': payment_order.order_id,
                'paymentId': validated_data['razorpay_payment_id'],
                'capturedAmount': validated_data['amount'],
                'status': 'paid'
            }
        }, status=status.HTTP_200_OK)
        
    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay capture error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Payment capture failed',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error capturing payment: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refund_payment(request, paymentId):
    """
    Refund a payment
    """
    try:
        serializer = PaymentRefundSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        # Get payment order
        try:
            payment_order = PaymentOrder.objects.get(id=paymentId, status='paid')
        except PaymentOrder.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Paid payment order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Determine refund amount
        refund_amount = validated_data.get('amount', payment_order.amount)
        
        if refund_amount > payment_order.amount:
            return Response({
                'success': False,
                'error': 'Refund amount cannot exceed payment amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert amount to paise
        amount_in_paise = int(refund_amount * 100)
        
        # Create refund via Razorpay
        refund_data = {
            'amount': amount_in_paise,
            'notes': {
                'order_id': payment_order.order_id,
                'reason': validated_data.get('reason', 'Customer request')
            }
        }
        
        razorpay_refund = razorpay_client.payment.refund(
            payment_order.razorpay_payment_id,
            refund_data
        )
        
        # Create refund record
        payment_refund = PaymentRefund.objects.create(
            payment_order=payment_order,
            razorpay_refund_id=razorpay_refund['id'],
            amount=refund_amount,
            reason=validated_data.get('reason', 'Customer request'),
            status='processed',
            processed_at=timezone.now()
        )
        
        # Update payment order status
        total_refunded = payment_order.refunds.filter(status='processed').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        if total_refunded >= payment_order.amount:
            payment_order.status = 'refunded'
        else:
            payment_order.status = 'partially_refunded'
        
        payment_order.save()
        
        logger.info(f"Payment refunded successfully: {payment_order.order_id}")
        
        return Response({
            'success': True,
            'message': 'Refund processed successfully',
            'data': {
                'orderId': payment_order.order_id,
                'refundId': razorpay_refund['id'],
                'refundAmount': refund_amount,
                'status': payment_order.status
            }
        }, status=status.HTTP_200_OK)
        
    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay refund error: {str(e)}")
        return Response({
            'success': False,
            'error': 'Refund failed',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error processing refund: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_status(request, paymentId):
    """
    Get payment status by payment ID
    """
    try:
        payment_order = get_object_or_404(PaymentOrder, id=paymentId)
        
        # Optionally sync with Razorpay for latest status
        if payment_order.razorpay_payment_id:
            try:
                razorpay_payment = razorpay_client.payment.fetch(payment_order.razorpay_payment_id)
                
                # Update status based on Razorpay status
                razorpay_status_mapping = {
                    'created': 'created',
                    'authorized': 'pending',
                    'captured': 'paid',
                    'refunded': 'refunded',
                    'failed': 'failed'
                }
                
                updated_status = razorpay_status_mapping.get(razorpay_payment['status'], payment_order.status)
                if updated_status != payment_order.status:
                    payment_order.status = updated_status
                    payment_order.save()
                    
            except Exception as e:
                logger.warning(f"Could not sync with Razorpay: {str(e)}")
        
        serializer = PaymentOrderResponseSerializer(payment_order)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error fetching payment status: {str(e)}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)