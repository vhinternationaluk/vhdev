from django.db import models
from django.utils import timezone
from accounts.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_name = models.CharField(max_length=50, blank=False, null=False)
    img_url = models.ImageField(upload_to='category_images/', null=True, blank=True)
    discount = models.IntegerField(default=0, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=100, blank=False)
    created_on = models.DateTimeField(default=timezone.now)
    modified_by = models.CharField(max_length=100, blank=False)
    modified_on = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'product_category'

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, blank=False, null=False)
    description = models.TextField(null=True, blank=True)
    cost = models.IntegerField(null=False, blank=False, default=0)
    quantity = models.IntegerField(null=False, blank=False, default=0)
    img_url = models.ImageField(upload_to='product_images/', null=True, blank=True)
    discount = models.IntegerField(default=0, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=100, blank=False)
    created_on = models.DateTimeField(default=timezone.now)
    modified_by = models.CharField(max_length=100, blank=False)
    modified_on = models.DateTimeField(default=timezone.now)
    product_category = models.ForeignKey(ProductCategory, null=True, blank=True, on_delete=models.DO_NOTHING)
    no_of_purchase=models.IntegerField(default=0)
    class Meta:
        db_table = 'product'

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_amount(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity
