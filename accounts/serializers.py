from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User,Address
import re
from .utils import upload_file_to_s3
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    profile_img = serializers.ImageField(required=False, allow_null=True, write_only=True)
    # profile_img_url = serializers.URLField(read_only=True)  

    class Meta:
        model = User
        fields = ('username', 'email', 'password','mobile',  'first_name', 'last_name','profile_img')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value


    def create(self, validated_data):
        profile_img = validated_data.pop('profile_img', None)
        
        # Create user without image first
        user = User.objects.create_user(
            user_type='common',
            **validated_data
        )
        
        # Handle custom image upload
        if profile_img:
            s3_url = upload_file_to_s3(profile_img, "profile_images")
            if s3_url:
                # Store the S3 URL in a custom field or handle as needed
                user.profile_img = s3_url
                user.save()
            else:
                # Handle upload failure
                raise serializers.ValidationError("Failed to upload profile image")
        
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled')
            attrs['user'] = user
        return attrs

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email not found")
        return value

class GoogleLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'user_type', 'created_at')

class UserSerializer(serializers.ModelSerializer):


    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'mobile', 'user_type', 'profile_img']

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Detailed user profile serializer
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'phone', 'date_of_birth', 'profile_picture', 'bio', 
                 'user_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'username', 'user_type', 'created_at', 'updated_at']

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value


class AddressSerializer(serializers.ModelSerializer):
    """
    Address serializer
    """
    class Meta:
        model = Address
        fields = ['id', 'address_type', 'street_address', 'apartment', 
                 'city', 'state', 'postal_code', 'country', 'is_default', 
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        user = self.context['request'].user
        address_type = attrs.get('address_type')
        
        # Check if address type already exists for this user (for creation)
        if not self.instance:  # Creating new address
            if Address.objects.filter(user=user, address_type=address_type).exists():
                raise serializers.ValidationError(
                    f"Address with type '{address_type}' already exists for this user"
                )
        
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


