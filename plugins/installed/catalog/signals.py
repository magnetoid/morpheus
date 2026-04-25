from django.db.models.signals import post_save
from django.dispatch import receiver
from core.hooks import hook_registry, MorpheusEvents
from .models import Product

@receiver(post_save, sender=Product)
def product_post_save(sender, instance, created, **kwargs):
    if created:
        hook_registry.fire(MorpheusEvents.PRODUCT_CREATED, product=instance)
    else:
        hook_registry.fire(MorpheusEvents.PRODUCT_UPDATED, product=instance)
