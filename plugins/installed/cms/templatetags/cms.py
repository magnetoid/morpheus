"""CMS template tags — `{% cms_block "key" %}` and `{% cms_menu "key" %}`."""
from __future__ import annotations

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def cms_block(context, key: str):
    from plugins.installed.cms.services import render_block
    block = render_block(key)
    if block is None:
        return ''
    try:
        return render_to_string('cms/_block.html',
                                {'block': block}, request=context.get('request'))
    except Exception:  # noqa: BLE001
        return mark_safe(block.get('body', ''))


@register.simple_tag(takes_context=True)
def cms_menu(context, key: str):
    from plugins.installed.cms.services import get_menu
    menu = get_menu(key)
    if menu is None:
        return ''
    return render_to_string('cms/_menu.html',
                            {'menu': menu}, request=context.get('request'))


@register.simple_tag(takes_context=True)
def cms_form(context, key: str):
    from plugins.installed.cms.models import Form
    form = Form.objects.filter(key=key, is_active=True).first()
    if form is None:
        return ''
    return render_to_string('cms/_form.html',
                            {'form': form}, request=context.get('request'))
