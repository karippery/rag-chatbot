from rest_framework import permissions

class CanUploadPermission(permissions.BasePermission):
    """Only EMPLOYEE and above can upload documents."""
    message = "Only employees and above can upload documents."

    def has_permission(self, request, view):
        return request.user.role not in ["GUEST"]
    
class CanDeletePermission(permissions.BasePermission):
    """Only CEO and VICE_PRESIDENT can delete documents."""
    message = "Only CEO and VICE_PRESIDENT can delete documents."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role in ["CEO", "VICE_PRESIDENT"]