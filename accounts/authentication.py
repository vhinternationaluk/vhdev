from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from .utils import TokenManager

User = get_user_model()

class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = self.get_token_from_request(request)
        if not token:
            return None

        payload = TokenManager.verify_token(token)
        if not payload:
            raise AuthenticationFailed('Invalid token')
        if payload == 'expired':
            raise AuthenticationFailed('Token expired')

        try:
            user = User.objects.get(id=payload['user_id'])
            return (user, payload)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')

    def get_token_from_request(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header[7:]
        return None
