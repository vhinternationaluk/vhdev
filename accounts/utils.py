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
