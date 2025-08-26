from django.core.management.base import BaseCommand
from accounts.models import User
from order.models import Order, OrderItem, ShippingAddress, Billing, Payment
from decimal import Decimal
import uuid

class Command(BaseCommand):
    help = 'Create sample order data'

    def handle(self, *args, **options):
        # Create a test user if doesn't exist
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com'}
        )
        
        # Create sample order
        order = Order.objects.create(
            userId=user,
            status='pending'
        )
        
        # Create order items
        OrderItem.objects.create(
            order=order,
            productId='PROD001',
            name='Sample Product 1',
            quantity=2,
            price=Decimal('999.99'),
            totalPrice=Decimal('1999.98')
        )
        
        # Create shipping address
        ShippingAddress.objects.create(
            order=order,
            fullAddress='123 Main Street, Apartment 4B',
            city='Mumbai',
            state='Maharashtra',
            pincode='400001'
        )
        
        # Create billing
        Billing.objects.create(
            order=order,
            subtotal=Decimal('1999.98'),
            discount=Decimal('100.00'),
            tax=Decimal('180.00'),
            shippingCharges=Decimal('50.00'),
            totalAmount=Decimal('2129.98')
        )
        
        # Create payment
        Payment.objects.create(
            order=order,
            paymentId=f'pay_{uuid.uuid4().hex[:12]}',
            method='razorpay',
            status='pending'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created sample order: {order.orderId}')
        )