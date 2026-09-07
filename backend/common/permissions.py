from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Grants access only to users with role='admin'.
    Distinct from Django's built-in is_staff — we use an explicit
    role field so that admin access is controlled by the application,
    not by the Django admin site's superuser system.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class IsAdminOrOwner(BasePermission):
    """
    Object-level permission used by PolicyViewSet and ClaimViewSet.

    - Admins (role='admin') may access any object.
    - Customers may only access objects they own:
        - Policy: obj.user == request.user
        - Claim:  obj.submitted_by == request.user

    The list-level queryset filtering (customers only see their own
    records) is the first line of defence; this permission is the
    second line, guarding individual object retrieval/mutation so that
    a customer cannot access another's record by guessing an ID.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True

        # Policy objects expose .user; Claim objects expose .submitted_by
        owner = getattr(obj, 'user', None) or getattr(obj, 'submitted_by', None)
        return owner == request.user
