import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from core.models import APIKey

logger = logging.getLogger('morpheus.api.auth')

class AgentAuthMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate Agent-to-Agent (A2A) Protocol requests.
    Validates the Bearer token against the APIKey model and injects capabilities.
    """
    def process_request(self, request):
        # We only care about requests hitting the agent endpoint
        if not request.path.startswith('/graphql/agent/'):
            return None

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Unauthorized: Missing or invalid Bearer token'}, status=401)

        token = auth_header.split(' ')[1]

        try:
            api_key = APIKey.objects.get(key=token, is_active=True)
            
            # Inject AgentCapabilities into the request so strawberry context can access them
            request.agent_capabilities = {
                'scopes': api_key.scopes,
                'channel_id': api_key.channel_id if api_key.channel else None,
                'is_agent': True
            }
            logger.info(f"Authenticated Agent: {api_key.name}")
        except APIKey.DoesNotExist:
            return JsonResponse({'error': 'Unauthorized: Invalid Agent Token'}, status=401)

        return None
