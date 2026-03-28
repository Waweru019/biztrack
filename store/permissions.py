
from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == 'admin'

class IsCashierUser(permissions.BasePermission):
    def has_permission(self, request, view):
        # Admins can also act as cashiers
        return request.user.is_authenticated and request.user.profile.role in ['admin', 'cashier']