from rest_framework.decorators import api_view, permission_classes,parser_classes
from rest_framework.response import Response
from rest_framework import status, generics
from django.shortcuts import get_object_or_404
from .models import ProductCategory, Product
from .serializer import *
from django.db import transaction
from .permissions import IsAdminOrSuperAdmin
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

# Product Category APIs (admin/superadmin only)
@api_view(['GET'])
@permission_classes([IsAdminOrSuperAdmin])
def category_list(request):
    categories = ProductCategory.objects.all()
    serializer = ProductCategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminOrSuperAdmin])
@parser_classes([MultiPartParser, FormParser])
def category_create(request):
    serializer = ProductCategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAdminOrSuperAdmin])
def category_detail(request, pk):
    category = get_object_or_404(ProductCategory, pk=pk)
    serializer = ProductCategorySerializer(category)
    return Response(serializer.data)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminOrSuperAdmin])
@parser_classes([MultiPartParser, FormParser])
def category_update(request, pk):
    category = get_object_or_404(ProductCategory, pk=pk)
    serializer = ProductCategorySerializer(category, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAdminOrSuperAdmin])
def category_delete(request, pk):
    category = get_object_or_404(ProductCategory, pk=pk)
    category.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

# Product APIs (admin/superadmin for write, everyone can read)

# Create product (admin/superadmin)
@api_view(['POST'])
@permission_classes([IsAdminOrSuperAdmin])
@parser_classes([MultiPartParser, FormParser])
def product_create(request):
    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Update product (admin/superadmin)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminOrSuperAdmin])
@parser_classes([MultiPartParser, FormParser])
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    serializer = ProductSerializer(product, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Delete product (admin/superadmin)
@api_view(['DELETE'])
@permission_classes([IsAdminOrSuperAdmin])
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

# Get product list (accessible by any user)
@api_view(['GET'])
def product_list(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

# Get product by id (accessible by any user)
@api_view(['GET'])
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    serializer = ProductSerializer(product)
    return Response(serializer.data)

# Get products by category id (accessible by any user)
@api_view(['GET'])
def products_by_category(request, category_id):
    products = Product.objects.filter(product_category_id=category_id)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


class CartAPIView(generics.RetrieveAPIView):
    """
    GET /api/cart - Retrieve user's cart with all items
    """
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    """
    POST /api/cart/items - Add item to cart or update quantity if exists
    """
    serializer = AddToCartSerializer(data=request.data)
    if serializer.is_valid():
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        
        product = get_object_or_404(Product, id=product_id)
        
        # Check stock availability
        if product.stock_quantity < quantity:
            return Response(
                {'error': f'Only {product.stock_quantity} items available in stock.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        with transaction.atomic():
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not item_created:
                # Item already exists, update quantity
                new_quantity = cart_item.quantity + quantity
                if product.stock_quantity < new_quantity:
                    return Response(
                        {'error': f'Cannot add {quantity} items. Only {product.stock_quantity - cart_item.quantity} more available.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                cart_item.quantity = new_quantity
                cart_item.save()
        
        cart_serializer = CartSerializer(cart)
        return Response(cart_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_cart_item(request, itemId):
    """
    PUT /api/cart/items/{itemId} - Update cart item quantity
    """
    try:
        cart = Cart.objects.get(user=request.user)
        cart_item = get_object_or_404(CartItem, id=itemId, cart=cart)
    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UpdateCartItemSerializer(data=request.data)
    if serializer.is_valid():
        quantity = serializer.validated_data['quantity']
        
        # Check stock availability
        if cart_item.product.stock_quantity < quantity:
            return Response(
                {'error': f'Only {cart_item.product.stock_quantity} items available in stock.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart_item.quantity = quantity
        cart_item.save()
        
        cart_serializer = CartSerializer(cart)
        return Response(cart_serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_cart_item(request, itemId):
    """
    DELETE /api/cart/items/{itemId} - Remove specific item from cart
    """
    try:
        cart = Cart.objects.get(user=request.user)
        cart_item = get_object_or_404(CartItem, id=itemId, cart=cart)
        cart_item.delete()
        
        cart_serializer = CartSerializer(cart)
        return Response(cart_serializer.data, status=status.HTTP_200_OK)
    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_cart(request):
    """
    DELETE /api/cart/clear - Remove all items from cart
    """
    try:
        cart = Cart.objects.get(user=request.user)
        cart.items.all().delete()
        
        cart_serializer = CartSerializer(cart)
        return Response(cart_serializer.data, status=status.HTTP_200_OK)
    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)

class CartSummaryAPIView(generics.RetrieveAPIView):
    """
    GET /api/cart/summary - Get cart summary (totals only)
    """
    serializer_class = CartSummarySerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart
