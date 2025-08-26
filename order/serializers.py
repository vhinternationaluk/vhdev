from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import Order, OrderItem, ShippingAddress, Billing, Payment


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['productId', 'name', 'quantity', 'price', 'totalPrice']
        
    def validate(self, data):
        # Validate that totalPrice matches quantity * price
        if 'quantity' in data and 'price' in data:
            expected_total = data['quantity'] * data['price']
            if 'totalPrice' in data and data['totalPrice'] != expected_total:
                raise serializers.ValidationError(
                    "totalPrice should equal quantity * price"
                )
            # Set totalPrice if not provided
            if 'totalPrice' not in data:
                data['totalPrice'] = expected_total
        return data


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = ['fullAddress', 'city', 'state', 'pincode']


class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Billing
        fields = ['subtotal', 'discount', 'tax', 'shippingCharges', 'totalAmount']
        
    def validate(self, data):
        # Validate that totalAmount is calculated correctly
        if all(field in data for field in ['subtotal', 'discount', 'tax', 'shippingCharges']):
            expected_total = (
                data['subtotal'] - data['discount'] + 
                data['tax'] + data['shippingCharges']
            )
            if 'totalAmount' in data and data['totalAmount'] != expected_total:
                raise serializers.ValidationError(
                    "totalAmount calculation is incorrect"
                )
            # Set totalAmount if not provided
            if 'totalAmount' not in data:
                data['totalAmount'] = expected_total
        return data


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['paymentId', 'method', 'status']


class OrderSerializer(serializers.ModelSerializer):
    orderId = serializers.UUIDField(read_only=True)
    userId = serializers.StringRelatedField(read_only=True)
    items = OrderItemSerializer(many=True)
    shippingAddress = ShippingAddressSerializer()
    billing = BillingSerializer()
    payment = PaymentSerializer()
    
    class Meta:
        model = Order
        fields = [
            'orderId', 'userId', 'status', 'orderDate', 'deliveryDate',
            'items', 'shippingAddress', 'billing', 'payment'
        ]
        read_only_fields = ['orderId', 'orderDate']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        shipping_data = validated_data.pop('shippingAddress')
        billing_data = validated_data.pop('billing')
        payment_data = validated_data.pop('payment')
        
        # Create order
        order = Order.objects.create(**validated_data)
        
        # Create related objects
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        ShippingAddress.objects.create(order=order, **shipping_data)
        Billing.objects.create(order=order, **billing_data)
        Payment.objects.create(order=order, **payment_data)
        
        return order
    
    def update(self, instance, validated_data):
        # Handle nested updates
        items_data = validated_data.pop('items', None)
        shipping_data = validated_data.pop('shippingAddress', None)
        billing_data = validated_data.pop('billing', None)
        payment_data = validated_data.pop('payment', None)
        
        # Update order fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update related objects if provided
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                OrderItem.objects.create(order=instance, **item_data)
        
        if shipping_data is not None:
            ShippingAddress.objects.update_or_create(
                order=instance, defaults=shipping_data
            )
        
        if billing_data is not None:
            Billing.objects.update_or_create(
                order=instance, defaults=billing_data
            )
        
        if payment_data is not None:
            Payment.objects.update_or_create(
                order=instance, defaults=payment_data
            )
        
        return instance


class OrderCreateSerializer(OrderSerializer):
    userId = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True
    )
    
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields
        read_only_fields = ['orderId', 'orderDate']


class OrderTrackingSerializer(serializers.ModelSerializer):
    orderId = serializers.UUIDField(read_only=True)
    userId = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Order
        fields = ['orderId', 'userId', 'status', 'orderDate', 'deliveryDate']


class OrderReturnSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
    returnDate = serializers.DateTimeField(read_only=True)
