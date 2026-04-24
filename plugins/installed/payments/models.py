import uuid
from django.db import models
from djmoney.models.fields import MoneyField

class PaymentMethod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='payment_methods', null=True, blank=True)
    provider = models.CharField(max_length=50, default='stripe')
    provider_id = models.CharField(max_length=128, help_text="e.g., pm_123456789")
    is_default = models.BooleanField(default=False)
    last4 = models.CharField(max_length=4, blank=True)
    brand = models.CharField(max_length=50, blank=True)

    class Meta:
        app_label = 'plugins'

    def __str__(self):
        return f"{self.brand} ending in {self.last4}"

class PaymentTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Meta:
        app_label = 'plugins'
        
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='transactions')
    amount = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=50, default='stripe')
    provider_transaction_id = models.CharField(max_length=128, blank=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Tx {self.id} for Order {self.order.order_number} - {self.status}"
