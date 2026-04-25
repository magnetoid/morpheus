from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
from core.models import StoreSettings

class MorpheusEmailBackend(EmailBackend):
    """
    A custom email backend that reads SMTP configuration from the StoreSettings singleton 
    (the Dashboard) rather than environment variables, allowing admins to change email providers on the fly.
    """
    def __init__(self, fail_silently=False, **kwargs):
        # Default to settings.py
        host = getattr(settings, 'EMAIL_HOST', '')
        port = getattr(settings, 'EMAIL_PORT', 587)
        username = getattr(settings, 'EMAIL_HOST_USER', '')
        password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        
        # Attempt to override from Database
        try:
            store_settings = StoreSettings.objects.first()
            if store_settings and store_settings.smtp_host:
                host = store_settings.smtp_host
                port = store_settings.smtp_port
                username = store_settings.smtp_user
                password = store_settings.smtp_password
            if store_settings and store_settings.default_from_email:
                settings.DEFAULT_FROM_EMAIL = store_settings.default_from_email
        except Exception:
            pass # DB might not be ready yet

        super().__init__(
            host=host, 
            port=port, 
            username=username, 
            password=password, 
            use_tls=use_tls, 
            fail_silently=fail_silently, 
            **kwargs
        )
