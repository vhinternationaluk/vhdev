from rest_framework import serializers
from .models import PaymentOrder, PaymentRefund
from django.contrib.auth.models import User

class CustomerDetailsSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=15)

class CreateOrderSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='INR')
    orderId = serializers.CharField(max_length=100)
    userId = serializers.CharField(max_length=100)
    customerDetails = CustomerDetailsSerializer()
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def validate_currency(self, value):
        if value not in ['INR', 'USD', 'EUR']:
            raise serializers.ValidationError("Invalid currency")
        return value

class PaymentVerificationSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=500)
    orderId = serializers.CharField(max_length=100)

class PaymentCaptureSerializer(serializers.Serializer):
    razorpay_payment_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    orderId = serializers.CharField(max_length=100)

class PaymentRefundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    reason = serializers.CharField(max_length=500, required=False)

class PaymentOrderResponseSerializer(serializers.ModelSerializer):
    customerDetails = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentOrder
        fields = [
            'id', 'order_id', 'razorpay_order_id', 'amount', 'currency',
            'status', 'customerDetails', 'created_at', 'updated_at'
        ]
    
    def get_customerDetails(self, obj):
        return {
            'name': obj.customer_name,
            'email': obj.customer_email,
            'phone': obj.customer_phone
        }