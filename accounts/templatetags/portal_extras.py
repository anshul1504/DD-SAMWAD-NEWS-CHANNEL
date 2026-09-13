from django import template
from django.core.exceptions import FieldDoesNotExist

register = template.Library()


@register.simple_tag
def portal_column_label(model, field_name):
    """Verbose name for a PORTAL_MODULES list column."""
    try:
        return model._meta.get_field(field_name).verbose_name
    except (FieldDoesNotExist, AttributeError):
        return field_name.replace("_", " ")


@register.simple_tag
def portal_column_value(instance, field_name):
    """Display value for a PORTAL_MODULES list column.

    Choice fields resolve through get_FOO_display so the portal shows
    "Published" rather than the stored "published".
    """
    display = getattr(instance, f"get_{field_name}_display", None)
    if callable(display):
        return display()
    value = getattr(instance, field_name, "")
    if value is None:
        return ""
    return value
