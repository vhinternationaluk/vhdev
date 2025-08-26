from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import logout
from django.core.mail import send_mail
from django.conf import settings
from google.auth.transport import requests
from google.oauth2 import id_token
from .serializers import *
from .utils import CustomResponse, TokenManager
from .models import User, RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from .models import User
from .serializers import UserSerializer
import logging

logger = logging.getLogger(__name__)

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        try:
            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                user_data = UserSerializer(user).data
                response_data, status_code = CustomResponse.success(
                    data=user_data,
                    message="User registered successfully"
                )
                return Response(response_data, status=status_code)
            else:
                response_data, status_code = CustomResponse.error(
                    message="Validation failed",
                    status_code=400
                )
                response_data['payload'] = serializer.errors
                return Response(response_data, status=status_code)
        except Exception as e:
            response_data, status_code = CustomResponse.error(
                message="Registration failed",
                status_code=500,
                exception_details=e
            )
            return Response(response_data, status=status_code)

class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = UserLoginSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                access_token, refresh_token = TokenManager.generate_tokens(user)
                
                response_data = {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'expires_in': 600  # 10 minutes in seconds
                }
                
                response, status_code = CustomResponse.success(
                    data=response_data,
                    message="Login successful"
                )
                return Response(response, status=status_code)
            else:
                response_data, status_code = CustomResponse.error(
                    message="Invalid credentials",
                    status_code=401
                )
                response_data['payload'] = serializer.errors
                return Response(response_data, status=status_code)
        except Exception as e:
            response_data, status_code = CustomResponse.error(
                message="Login failed",
                status_code=500,
                exception_details=e
            )
            return Response(response_data, status=status_code)

class UserLogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                # Deactivate refresh token
                RefreshToken.objects.filter(
                    user=request.user,
                    token=refresh_token
                ).update(is_active=False)
            
            response_data, status_code = CustomResponse.success(
                message="Logout successful"
            )
            return Response(response_data, status=status_code)
        except Exception as e:
            response_data, status_code = CustomResponse.error(
                message="Logout failed",
                status_code=500,
                exception_details=e
            )
            return Response(response_data, status=status_code)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                response_data, status_code = CustomResponse.error(
                    message="Refresh token required",
                    status_code=400
                )
                return Response(response_data, status=status_code)

            new_access_token, user = TokenManager.refresh_access_token(refresh_token)
            if not new_access_token:
                response_data, status_code = CustomResponse.error(
                    message="Invalid or expired refresh token",
                    status_code=401
                )
                return Response(response_data, status=status_code)

            response_data = {
                'access_token': new_access_token,
                'expires_in': 600  # 10 minutes
            }
            
            response, status_code = CustomResponse.success(
                data=response_data,
                message="Token refreshed successfully"
            )
            return Response(response, status=status_code)
        except Exception as e:
            response_data, status_code = CustomResponse.error(
                message="Token refresh failed",
                status_code=500,
                exception_details=e
            )
            return Response(response_data, status=status_code)

class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = PasswordResetSerializer(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                user = User.objects.get(email=email)
                
                # Generate password reset token
                token = default_token_generator.make_token(user)
                
                # In production, send email with reset link
                # For now, just return the token in response
                reset_link = f"http://localhost:8000/reset-password/{user.id}/{token}/"
                
                # Send email (console backend for development)
                send_mail(
                    'Password Reset',
                    f'Click here to reset your password: {reset_link}',
                    'from@example.com',
                    [email],
                    fail_silently=False,
                )
                
                response_data, status_code = CustomResponse.success(
                    data={'reset_link': reset_link},
                    message="Password reset email sent"
                )
                return Response(response_data, status=status_code)
            else:
                response_data, status_code = CustomResponse.error(
                    message="Validation failed",
                    status_code=400
                )
                response_data['payload'] = serializer.errors
                return Response(response_data, status=status_code)
        except Exception as e:
            response_data, status_code = CustomResponse.error(
                message="Password reset failed",
                status_code=500,
                exception_details=e
            )
            return Response(response_data, status=status_code)

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = GoogleLoginSerializer(data=request.data)
            if serializer.is_valid():
                token = serializer.validated_data['access_token']
                
                # Verify Google token
                try:
                    idinfo = id_token.verify_oauth2_token(
                        token, requests.Request(), settings.GOOGLE_OAUTH2_CLIENT_ID
                    )
                    
                    google_id = idinfo['sub']
                    email = idinfo['email']
                    name = idinfo.get('name', '')
                    
                    # Get or create user
                    user, created = User.objects.get_or_create(
                        google_id=google_id,
                        defaults={
                            'username': email,
                            'email': email,
                            'first_name': name.split(' ')[0] if name else '',
                            'last_name': ' '.join(name.split(' ')[1:]) if ' ' in name else '',
                            'user_type': 'common'
                        }
                    )
                    
                    access_token, refresh_token = TokenManager.generate_tokens(user)
                    
                    response_data = {
                        'user': UserSerializer(user).data,
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'expires_in': 600,
                        'is_new_user': created
                    }
                    
                    response, status_code = CustomResponse.success(
                        data=response_data,
                        message="Google login successful"
                    )
                    return Response(response, status=status_code)
                    
                except ValueError as e:
                    response_data, status_code = CustomResponse.error(
                        message="Invalid Google token",
                        status_code=401,
                        exception_details=e
                    )
                    return Response(response_data, status=status_code)
            else:
                response_data, status_code = CustomResponse.error(
                    message="Validation failed",
                    status_code=400
                )
                response_data['payload'] = serializer.errors
                return Response(response_data, status=status_code)
        except Exception as e:
            response_data, status_code = CustomResponse.error(
                message="Google login failed",
                status_code=500,
                exception_details=e
            )
            return Response(response_data, status=status_code)

class UserProfileView(APIView):
    def get(self, request):
        try:
            user_data = UserSerializer(request.user).data
            response_data, status_code = CustomResponse.success(
                data=user_data,
                message="Profile retrieved successfully"
            )
            return Response(response_data, status=status_code)
        except Exception as e:
            response_data, status_code = CustomResponse.error(
                message="Failed to retrieve profile",
                status_code=500,
                exception_details=e
            )
            return Response(response_data, status=status_code)




# Custom Permission to allow only admin or superadmin
class IsAdminOrSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_or_above

# 1. GET USER LIST (Only for admin or superadmin)
@api_view(['GET'])
@permission_classes([IsAdminOrSuperAdmin])
def get_user_list(request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# 2. GET USER BY ID (Only for admin or superadmin)
@api_view(['GET'])
@permission_classes([IsAdminOrSuperAdmin])
def get_user_by_id(request, pk):
    user = get_object_or_404(User, pk=pk)
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)

# 3. UPDATE USER BY ID (Only for admin or superadmin)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminOrSuperAdmin])
def update_user_by_id(request, pk):
    user = get_object_or_404(User, pk=pk)
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 4. DELETE USER (Only for admin or superadmin)
@api_view(['DELETE'])
@permission_classes([IsAdminOrSuperAdmin])
def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.delete()
    return Response({"message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

# User Profile Management Views
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    GET: Retrieve current user's profile
    PUT: Update current user's profile
    """
    user = request.user
    
    if request.method == 'GET':
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = UserProfileSerializer(
            user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Address Management Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_addresses(request):
    """
    GET: List all addresses for current user
    POST: Create new address for current user
    """
    user = request.user
    
    if request.method == 'GET':
        addresses = Address.objects.filter(user=user)
        serializer = AddressSerializer(addresses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = AddressSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            address = serializer.save()
            return Response({
                'message': 'Address created successfully',
                'address': AddressSerializer(address).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_address_detail(request, address_id):
    """
    PUT: Update specific address
    DELETE: Delete specific address
    """
    user = request.user
    
    try:
        address = Address.objects.get(id=address_id, user=user)
    except Address.DoesNotExist:
        return Response({
            'error': 'Address not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'PUT':
        serializer = AddressSerializer(
            address,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Address updated successfully',
                'address': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        address.delete()
        return Response({
            'message': 'Address deleted successfully'
        }, status=status.HTTP_200_OK)


class UserIsAdminView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Return if the authenticated user is admin or above
        is_admin = getattr(request.user, 'is_admin_or_above', False)
        return Response({'is_admin': is_admin})