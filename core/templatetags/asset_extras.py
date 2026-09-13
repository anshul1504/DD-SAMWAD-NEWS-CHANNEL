import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(path):
    """Static URL with a cache-busting ?v=<mtime> query so edited CSS/JS
    is never served stale from the browser cache after a deploy."""
    url = static(path)
    absolute_path = finders.find(path)
    if not absolute_path:
        return url
    try:
        version = int(os.path.getmtime(absolute_path))
    except OSError:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={version}"
