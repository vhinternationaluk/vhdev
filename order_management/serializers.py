# orders/serializers.py

from rest_framework import serializers
from .models import Order, Product, ShippingAddress, BillingAddress, Billing


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status'] # Only the 'status' field is updatable

class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        exclude = ['order']

class BillingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingAddress
        exclude = ['order']

class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Billing
        read_only_fields = ('subtotal', 'totalAmount')
        exclude = ['order']

class OrderSerializer(serializers.ModelSerializer):
    """Serializer for reading and updating order details."""
    user = serializers.ReadOnlyField(source='user.username')
    product_name = serializers.CharField(source='product.name', read_only=True)
    shipping_address = ShippingAddressSerializer(read_only=True)
    billing_address = BillingAddressSerializer(read_only=True)
    billing = BillingSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'product', 'product_name', 'quantity', 
            'status', 'is_paid', 'shipping_address', 'billing_address', 'billing', 'created_at'
        ]
        extra_kwargs = {'product': {'write_only': True}}

class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new order with all related details."""
    product_id = serializers.UUIDField(write_only=True)
    shipping_address = ShippingAddressSerializer(write_only=True)
    billing_address = BillingAddressSerializer(write_only=True)
    billing = BillingSerializer(write_only=True)

    class Meta:
        model = Order
        fields = ['product_id', 'quantity', 'shipping_address', 'billing_address', 'billing']

    def create(self, validated_data):
        # Extract nested data for related models
        shipping_address_data = validated_data.pop('shipping_address')
        billing_address_data = validated_data.pop('billing_address')
        billing_data = validated_data.pop('billing')
        product_id = validated_data.pop('product_id')
        
        # Get the authenticated user from the JWT token via request context
        user = self.context['request'].user
        quantity = validated_data.get('quantity')

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")

        # 1. Create the Order instance, associating it with the user
        order = Order.objects.create(user=user, product=product, **validated_data)

        # 2. Create the related address and billing records, linking them to the new order
        ShippingAddress.objects.create(order=order, **shipping_address_data)
        BillingAddress.objects.create(order=order, **billing_address_data)
        
        subtotal = product.cost * quantity
        Billing.objects.create(order=order, subtotal=subtotal, **billing_data)
        
        order.refresh_from_db()
        return order
