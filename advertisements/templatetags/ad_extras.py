from django import template

register = template.Library()


@register.filter
def by_placement(ads, placement):
    if not ads:
        return []
    return [ad for ad in ads if ad.placement == placement]
