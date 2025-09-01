# orders/permissions.py

from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    """Custom permission to only allow owners of an object to access it."""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsAdminOrSuperUser(permissions.BasePermission):
    """
    Allows access only to admin users (is_staff=True).
    This is a more explicit name for DRF's built-in IsAdminUser.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff