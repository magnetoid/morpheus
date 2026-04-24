"""Core context processors — store settings and cart into every template."""
from django.conf import settings as django_settings


def store_settings(request):
    return {
        'STORE_NAME': django_settings.STORE_NAME,
        'STORE_CURRENCY': django_settings.STORE_CURRENCY,
        'STORE_COUNTRY': django_settings.STORE_COUNTRY,
        'DEBUG': django_settings.DEBUG,
    }


def cart_context(request):
    """Lightweight cart item count for the nav bar."""
    count = 0
    try:
        if request.user.is_authenticated:
            from plugins.installed.orders.models import Cart
            cart = Cart.objects.filter(customer=request.user).order_by('-updated_at').first()
            if cart:
                count = cart.item_count
        else:
            session_key = request.session.session_key
            if session_key:
                from plugins.installed.orders.models import Cart
                cart = Cart.objects.filter(session_key=session_key).order_by('-updated_at').first()
                if cart:
                    count = cart.item_count
    except Exception:
        pass
    return {'cart_item_count': count}
