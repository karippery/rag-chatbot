
from rest_framework import permissions

class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ["CEO", "VICE_PRESIDENT"] or request.user.is_staff