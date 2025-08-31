import jwt
import datetime
from django.conf import settings
from django.utils import timezone
from .models import RefreshToken, User
import traceback
import sys

class CustomResponse:
    @staticmethod
    def success(data=None, message="Success", status_code=200):
        return {
            "status": True,
            "status_message": message,
            "payload": data,
            "exception": None
        }, status_code

    @staticmethod
    def error(message="Error occurred", status_code=400, exception_details=None):
        exception_data = None
        if exception_details:
            exception_data = {
                "exception_source": str(type(exception_details).__name__),
                "exception_trackback": traceback.format_exc(),
                "exception_message": str(exception_details)
            }
        
        return {
            "status": False,
            "status_message": message,
            "payload": None,
            "exception": exception_data
        }, status_code

class TokenManager:
    @staticmethod
    def generate_tokens(user):
        # Access token (10 minutes)
        access_payload = {
            'user_id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'exp': timezone.now() + datetime.timedelta(minutes=10),
            'iat': timezone.now(),
            'token_type': 'access'
        }
        access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')

        # Refresh token (7 days)
        refresh_payload = {
            'user_id': user.id,
            'exp': timezone.now() + datetime.timedelta(days=7),
            'iat': timezone.now(),
            'token_type': 'refresh'
        }
        refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')

        # Store refresh token in database
        RefreshToken.objects.create(
            user=user,
            token=refresh_token,
            expires_at=timezone.now() + datetime.timedelta(days=7)
        )

        return access_token, refresh_token

    @staticmethod
    def verify_token(token, token_type='access'):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            if payload.get('token_type') != token_type:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return 'expired'
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def refresh_access_token(refresh_token):
        payload = TokenManager.verify_token(refresh_token, 'refresh')
        if not payload or payload == 'expired':
            return None, None

        try:
            # Check if refresh token exists in database
            token_obj = RefreshToken.objects.get(
                token=refresh_token,
                is_active=True,
                expires_at__gt=timezone.now()
            )
            user = token_obj.user

            # Generate new access token
            access_payload = {
                'user_id': user.id,
                'username': user.username,
                'user_type': user.user_type,
                'exp': timezone.now() + datetime.timedelta(minutes=10),
                'iat': timezone.now(),
                'token_type': 'access'
            }
            new_access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')

            return new_access_token, user
        except RefreshToken.DoesNotExist:
            return None, None


import boto3
import os
import uuid
from django.conf import settings
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

def upload_file_to_s3(file, folder_name="uploads"):
    """
    Custom function to upload files directly to S3
    Returns the S3 URL if successful, None if failed
    """
    try:
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
        )
        
        # Generate unique filename
        file_extension = file.name.split('.')[-1]
        unique_filename = f"{folder_name}/{uuid.uuid4()}.{file_extension}"
        
        # Upload file
        s3_client.upload_fileobj(
            file,
            os.environ.get('AWS_STORAGE_BUCKET_NAME'),
            unique_filename,
            ExtraArgs={
                'ContentType': file.content_type,
                'ACL': 'public-read'  # Make file publicly accessible
            }
        )
        
        # Return S3 URL
        bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{unique_filename}"
        
        logger.info(f"File uploaded successfully to: {s3_url}")
        return s3_url
        
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        return None
