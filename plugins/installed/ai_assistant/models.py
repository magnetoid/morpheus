import uuid
from django.db import models

class DynamicPriceRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField('catalog.Product', on_delete=models.CASCADE, related_name='dynamic_price_rule')
    multiplier = models.DecimalField(max_digits=5, decimal_places=4, default=1.0000)
    reasoning = models.TextField(blank=True, help_text="AI reasoning for this price adjustment")
    last_evaluated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'plugins'
        verbose_name = "Dynamic Price Rule"
        verbose_name_plural = "Dynamic Price Rules"

    def __str__(self):
        return f"Rule for {self.product.name} (x{self.multiplier})"
