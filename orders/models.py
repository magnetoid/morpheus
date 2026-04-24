"""
Morpheus CMS - Orders Models
Cart → Order → Fulfillment pipeline
"""
import uuid
from django.db import models
from djmoney.models.fields import MoneyField
from django.utils import timezone


class Cart(models.Model):
    """Session or customer cart."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        null=True, blank=True, related_name='carts'
    )
    session_key = models.CharField(max_length=100, blank=True)
    coupon = models.ForeignKey(
        'marketing.Coupon', on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        owner = self.customer.email if self.customer else self.session_key
        return f"Cart({owner})"

    @property
    def subtotal(self):
        from django.db.models import Sum, F, DecimalField
        result = self.items.aggregate(
            total=Sum(F('quantity') * F('unit_price_amount'), output_field=DecimalField())
        )
        return result['total'] or 0

    @property
    def item_count(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey(
        'catalog.ProductVariant', on_delete=models.CASCADE, null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product', 'variant')

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('partially_fulfilled', 'Partially Fulfilled'),
        ('fulfilled', 'Fulfilled'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    email = models.EmailField()
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')

    # Pricing
    subtotal = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    shipping_total = MoneyField(max_digits=14, decimal_places=2, default_currency='USD', default=0)
    tax_total = MoneyField(max_digits=14, decimal_places=2, default_currency='USD', default=0)
    discount_total = MoneyField(max_digits=14, decimal_places=2, default_currency='USD', default=0)
    total = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')

    # Addresses (snapshot at order time)
    shipping_address = models.JSONField(default=dict)
    billing_address = models.JSONField(default=dict)

    # Coupon
    coupon_code = models.CharField(max_length=50, blank=True)

    # Shipping
    shipping_method = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=200, blank=True)

    # Notes
    customer_notes = models.TextField(blank=True)
    staff_notes = models.TextField(blank=True)

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    source = models.CharField(max_length=50, default='web')  # web, api, pos, etc.

    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-placed_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['customer']),
        ]

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        import random, string
        prefix = 'MRP'
        suffix = ''.join(random.choices(string.digits, k=8))
        return f"{prefix}{suffix}"

    def cancel(self, reason=''):
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        if reason:
            self.staff_notes += f"\nCancelled: {reason}"
        self.save()


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)

    # Snapshot data (in case product changes)
    product_name = models.CharField(max_length=300)
    variant_name = models.CharField(max_length=200, blank=True)
    sku = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)

    quantity = models.PositiveIntegerField()
    unit_price = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    total_price = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')

    # Fulfillment
    fulfilled_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['product_name']

    def __str__(self):
        return f"{self.quantity}x {self.product_name} (Order #{self.order.order_number})"


class Fulfillment(models.Model):
    """Tracks shipment of order items."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('returned', 'Returned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='fulfillments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    tracking_number = models.CharField(max_length=200, blank=True)
    tracking_url = models.URLField(blank=True)
    carrier = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fulfillment for Order #{self.order.order_number}"


class FulfillmentItem(models.Model):
    fulfillment = models.ForeignKey(Fulfillment, on_delete=models.CASCADE, related_name='items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity}x {self.order_item.product_name}"


class Refund(models.Model):
    """Order refunds."""
    REASON_CHOICES = [
        ('customer_request', 'Customer Request'),
        ('defective', 'Defective Product'),
        ('not_as_described', 'Not As Described'),
        ('wrong_item', 'Wrong Item Sent'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    amount = MoneyField(max_digits=14, decimal_places=2, default_currency='USD')
    reason = models.CharField(max_length=25, choices=REASON_CHOICES, default='other')
    notes = models.TextField(blank=True)
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Refund {self.amount} for Order #{self.order.order_number}"
