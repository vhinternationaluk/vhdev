from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .utils import CustomResponse
import json

class TokenExceptionMiddleware(MiddlewareMixin):
    """
    Middleware to catch authentication errors and return custom response format
    """
    def process_exception(self, request, exception):
        if hasattr(exception, 'status_code') and exception.status_code == 401:
            response_data, status_code = CustomResponse.error(
                message="Authentication failed - Token expired or invalid",
                status_code=401
            )
            return JsonResponse(response_data, status=status_code)
        return None