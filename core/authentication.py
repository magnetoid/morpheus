"""
Morpheus CMS — API Key Authentication & RBAC
Enforces scopes for external headless clients and Remote Plugins.
"""
from rest_framework import authentication
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _
from core.models import APIKey

class MorpheusAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Validates the `Authorization: Bearer <key>` header against `APIKey` records.
    Attaches the APIKey instance to the request for channel scoping and scope validation.
    """
    keyword = 'Bearer'

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token, request)

    def authenticate_credentials(self, key, request=None):
        try:
            # We look up the key. In production, we should cache this lookup.
            api_key = APIKey.objects.select_related('channel').get(key=key, is_active=True)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid API key.'))

        # Attach the api key to the request so viewsets can check scopes/channels
        request._morpheus_api_key = api_key
        
        # We return (None, api_key) because this isn't a "User".
        # This keeps request.user anonymous, but request.auth contains the APIKey.
        return (None, api_key)


class HasScopePermission:
    """
    DRF Permission class to check if the current APIKey has a required scope.
    Usage in ViewSet:
        permission_classes = [HasScope('read:products')]
    """
    def __init__(self, required_scope):
        self.required_scope = required_scope

    def __call__(self):
        return self

    def has_permission(self, request, view):
        # If it's a regular logged in user, maybe they have full access?
        # For this implementation, we enforce API Key scopes.
        if hasattr(request, '_morpheus_api_key'):
            return request._morpheus_api_key.has_scope(self.required_scope)
        
        # Fallback to session auth for admins
        return request.user and request.user.is_staff
