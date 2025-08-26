# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import uuid
from django.conf import settings


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    
    orderId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    userId = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    orderDate = models.DateTimeField(auto_now_add=True)
    deliveryDate = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-orderDate']
        
    def __str__(self):
        return f"Order {self.orderId} - {self.userId.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    productId = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    totalPrice = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    def save(self, *args, **kwargs):
        # Auto-calculate totalPrice if not provided
        if not self.totalPrice:
            self.totalPrice = self.quantity * self.price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} x {self.quantity}"


class ShippingAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shippingAddress')
    fullAddress = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    
    def __str__(self):
        return f"{self.city}, {self.state} - {self.pincode}"


class Billing(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='billing')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    shippingCharges = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    totalAmount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    def save(self, *args, **kwargs):
        # Auto-calculate totalAmount if not provided
        if not self.totalAmount:
            self.totalAmount = self.subtotal - self.discount + self.tax + self.shippingCharges
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Total: {self.totalAmount}"


class Payment(models.Model):
    METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('cod', 'Cash on Delivery'),
        ('wallet', 'Wallet'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    paymentId = models.CharField(max_length=100, unique=True)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment {self.paymentId} - {self.method} - {self.status}"