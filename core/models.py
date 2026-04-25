"""
Core models — StoreSettings only.
Vendor moved to catalog plugin to avoid circular migration dependency.
"""
import uuid
from django.db import models


class StoreSettings(models.Model):
    """Global store configuration singleton."""
    store_name = models.CharField(max_length=200, default='Morpheus Store')
    store_description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='store/', blank=True, null=True)
    favicon = models.ImageField(upload_to='store/', blank=True, null=True)
    primary_currency = models.CharField(max_length=3, default='USD')
    country = models.CharField(max_length=2, default='US')
    timezone = models.CharField(max_length=50, default='UTC')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    ai_provider = models.CharField(max_length=20, default='openai')
    contact_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    social_links = models.JSONField(default=dict)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Custom SMTP Overrides
    smtp_host = models.CharField(max_length=200, blank=True, help_text="e.g. smtp.resend.com")
    smtp_port = models.IntegerField(default=587)
    smtp_user = models.CharField(max_length=200, blank=True)
    smtp_password = models.CharField(max_length=200, blank=True)
    default_from_email = models.CharField(max_length=200, blank=True, help_text="e.g. noreply@dotbooks.shop")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Store Settings'
        verbose_name_plural = 'Store Settings'

    def __str__(self):
        return self.store_name

    @classmethod
    def get(cls, key: str, default=None):
        from django.db import DatabaseError
        try:
            obj = cls.objects.first()
        except DatabaseError:
            # DB unavailable (e.g. migrations not yet applied) — degrade gracefully.
            return default
        return getattr(obj, key, default) if obj else default

class StoreChannel(models.Model):
    """
    Enables headless multi-tenancy. A single Morpheus backend can serve 
    multiple storefronts (e.g., B2B wholesale portal, B2C main site, App channel).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.domain})"

class APIKey(models.Model):
    """
    Law 2: Secure Core. Granular RBAC for headless clients and Remote Plugins.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=64, unique=True, editable=False)
    scopes = models.JSONField(default=list, help_text="List of permitted scopes, e.g. ['read:products', 'write:orders']")
    channel = models.ForeignKey(StoreChannel, on_delete=models.CASCADE, null=True, blank=True, related_name='api_keys')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"API Key: {self.name}"

    def has_scope(self, scope: str) -> bool:
        return 'admin' in self.scopes or scope in self.scopes

    def save(self, *args, **kwargs):
        if not self.key:
            import secrets
            self.key = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)

class WebhookEndpoint(models.Model):
    """
    Subscribes external services (Remote Plugins) to Morpheus Events.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    url = models.URLField(help_text="The destination URL to POST event payloads")
    secret = models.CharField(max_length=255, blank=True, help_text="Used for HMAC signature verification")
    events = models.JSONField(default=list, help_text="List of event strings to subscribe to, e.g. ['order.placed']")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.url})"

class OutboxEvent(models.Model):
    """
    Implements the Transactional Outbox pattern.
    Events are written here in the same DB transaction as domain mutations.
    A separate worker reads these and publishes to NATS/Kafka.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=255, db_index=True)
    payload = models.JSONField()
    status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Pending'),
        ('PUBLISHED', 'Published'),
        ('FAILED', 'Failed')
    ], db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.event_type} - {self.status}"
