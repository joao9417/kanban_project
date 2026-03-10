"""
boards/templatetags/board_extras.py

Custom template filters used across the boards app.
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Returns dict[key] or None if key is absent.
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
