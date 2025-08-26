# admin.py
from django.contrib import admin
from .models import Order, OrderItem, ShippingAddress, Billing, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('totalPrice',)


class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress


class BillingInline(admin.StackedInline):
    model = Billing
    readonly_fields = ('totalAmount',)


class PaymentInline(admin.StackedInline):
    model = Payment


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('orderId', 'userId', 'status', 'orderDate', 'deliveryDate')
    list_filter = ('status', 'orderDate', 'deliveryDate')
    search_fields = ('orderId', 'userId__username', 'userId__email')
    readonly_fields = ('orderId', 'orderDate', 'created_at', 'updated_at')
    inlines = [OrderItemInline, ShippingAddressInline, BillingInline, PaymentInline]
    
    fieldsets = (
        (None, {
            'fields': ('orderId', 'userId', 'status', 'orderDate', 'deliveryDate')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'productId', 'name', 'quantity', 'price', 'totalPrice')
    list_filter = ('order__status',)
    search_fields = ('productId', 'name', 'order__orderId')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('paymentId', 'order', 'method', 'status', 'created_at')
    list_filter = ('method', 'status', 'created_at')
    search_fields = ('paymentId', 'order__orderId')


# ------------------------------
# requirements.txt
# ------------------------------
"""
Django>=4.2.0
djangorestframework>=3.14.0
django-cors-headers>=4.0.0
"""

# ------------------------------
# settings.py additions
# ------------------------------
"""
# Add to your INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'your_orders_app',  # Replace with your app name
]

# Add to MIDDLEWARE
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# CORS settings (if needed for frontend)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
"""

# ------------------------------
# Management Command for creating sample data
# management/commands/create_sample_orders.py
# ------------------------------
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from your_app.models import Order, OrderItem, ShippingAddress, Billing, Payment
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
"""