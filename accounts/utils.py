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

import boto3
import os
import uuid
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)

def upload_file_to_s3(file, folder_name="profile_images"):
    """
    Enhanced S3 upload with detailed error reporting
    """
    try:
        # Debug: Log environment variables (remove after debugging)
        logger.info("=== S3 Upload Debug Info ===")
        logger.info(f"AWS_ACCESS_KEY_ID exists: {bool(os.environ.get('AWS_ACCESS_KEY_ID'))}")
        logger.info(f"AWS_SECRET_ACCESS_KEY exists: {bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))}")
        logger.info(f"AWS_STORAGE_BUCKET_NAME: {os.environ.get('AWS_STORAGE_BUCKET_NAME')}")
        logger.info(f"AWS_S3_REGION_NAME: {os.environ.get('AWS_S3_REGION_NAME')}")
        logger.info(f"File name: {file.name}")
        logger.info(f"File size: {file.size}")
        logger.info(f"File content type: {file.content_type}")
        
        # Validate environment variables
        required_vars = {
            'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
            'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),
            'AWS_STORAGE_BUCKET_NAME': os.environ.get('AWS_STORAGE_BUCKET_NAME'),
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            logger.error(f"Missing environment variables: {missing_vars}")
            return {'success': False, 'error': f'Missing AWS config: {missing_vars}'}
        
        # Initialize S3 client with explicit credentials
        logger.info("Initializing S3 client...")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=required_vars['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=required_vars['AWS_SECRET_ACCESS_KEY'],
            region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
        )
        
        # Test S3 connection first
        logger.info("Testing S3 connection...")
        try:
            s3_client.head_bucket(Bucket=required_vars['AWS_STORAGE_BUCKET_NAME'])
            logger.info("S3 bucket access confirmed")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 bucket access failed: {error_code} - {e}")
            return {'success': False, 'error': f'S3 bucket access denied: {error_code}'}
        
        # Generate unique filename
        file_extension = file.name.split('.')[-1].lower()
        unique_filename = f"{folder_name}/{uuid.uuid4()}.{file_extension}"
        
        logger.info(f"Uploading to: {unique_filename}")
        
        # Reset file pointer to beginning
        file.seek(0)
        
        # Upload file
        s3_client.upload_fileobj(
            file,
            required_vars['AWS_STORAGE_BUCKET_NAME'],
            unique_filename,
            ExtraArgs={
                'ContentType': file.content_type or 'image/jpeg',

            }
        )
        
        # Generate S3 URL
        s3_url = f"https://{required_vars['AWS_STORAGE_BUCKET_NAME']}.s3.amazonaws.com/{unique_filename}"
        
        logger.info(f"Upload successful! URL: {s3_url}")
        return {'success': True, 'url': s3_url}
        
    except NoCredentialsError:
        logger.error("AWS credentials not found")
        return {'success': False, 'error': 'AWS credentials not found'}
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS ClientError: {error_code} - {error_message}")
        return {'success': False, 'error': f'AWS Error: {error_code} - {error_message}'}
    except Exception as e:
        logger.error(f"Unexpected upload error: {str(e)}")
        return {'success': False, 'error': f'Upload error: {str(e)}'}
