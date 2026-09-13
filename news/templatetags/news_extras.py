import datetime

from django import template
from django.utils import timezone

register = template.Library()

# Django's own bundled Hindi locale mis-spells month names (e.g. "सितमबर"
# instead of "सितंबर", missing the anusvara) -- a long-standing upstream
# typo in Django's translation catalog, not something fixable from our own
# code short of patching a third-party package. This filter renders the
# date ourselves with correct spelling instead of relying on the |date "F"
# placeholder, which is what every published-date/timestamp on the site uses.
HINDI_MONTHS = [
    "जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून",
    "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर",
]


@register.filter
def hindi_date(value, with_time=True):
    """Format a date/datetime as 'd Month Y[, h:i बजे]' with correctly
    spelled Hindi month names."""
    if not value:
        return ""
    # A plain date (e.g. EPaperEdition.edition_date) has no tzinfo at all --
    # timezone.is_aware() calls .utcoffset(), which only datetime defines.
    if isinstance(value, datetime.datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)
    day = value.day
    month = HINDI_MONTHS[value.month - 1]
    year = value.year
    if not with_time:
        return f"{day} {month} {year}"
    hour = value.hour % 12 or 12
    return f"{day} {month} {year}, {hour:02d}:{value.minute:02d} बजे"

# A fixed, professional editorial palette. Named categories get a
# meaningful color (politics=maroon, sports=green, business=blue, etc.);
# anything else is assigned deterministically from the same palette so a
# given category always renders the same color across the site.
CATEGORY_COLOR_KEYWORDS = [
    (("politic", "rajniti", "राजनीति", "नेता", "सरकार"), "#a3222c"),
    (("sport", "khel", "क्रिकेट", "खेल", "फुटबॉल"), "#0f7a4d"),
    (("entertain", "manoranjan", "bollywood", "मनोरंजन", "सिनेमा", "फिल्म"), "#9b2f8f"),
    (("business", "vyapar", "share", "बिज़नेस", "व्यापार", "बाजार", "शेयर"), "#0b5cab"),
    (("tech", "gadget", "टेक", "तकनीक"), "#0f766e"),
    (("health", "swasthya", "स्वास्थ्य", "सेहत"), "#059669"),
    (("education", "shiksha", "शिक्षा", "एजुकेशन", "एग्जाम", "रिजल्ट"), "#4338ca"),
    (("crime", "apradh", "क्राइम", "अपराध"), "#92400e"),
    (("world", "international", "vishwa", "विश्व", "दुनिया", "अंतरराष्ट्रीय"), "#1d3557"),
    (("religion", "dharma", "astrology", "धर्म", "ज्योतिष", "आध्यात्म"), "#b45309"),
    (("auto", "vehicle", "ऑटो", "गाड़ी"), "#475569"),
    (("lifestyle", "लाइफस्टाइल", "फैशन"), "#db2777"),
    (("national", "rashtriya", "राष्ट्रीय", "देश"), "#1e3a8a"),
    (("state", "rajya", "राज्य", "स्थानीय", "शहर"), "#c2410c"),
]

FALLBACK_PALETTE = [
    "#0b5cab", "#0f7a4d", "#9b2f8f", "#a3222c", "#0f766e",
    "#4338ca", "#c2410c", "#1d3557", "#b45309", "#475569",
]


CATEGORY_ICON_KEYWORDS = [
    (("politic", "rajniti", "राजनीति", "नेता", "सरकार"), "bi-bank"),
    (("sport", "khel", "क्रिकेट", "खेल", "फुटबॉल"), "bi-trophy"),
    (("entertain", "manoranjan", "bollywood", "मनोरंजन", "सिनेमा", "फिल्म"), "bi-camera-reels"),
    (("business", "vyapar", "share", "बिज़नेस", "व्यापार", "बाजार", "शेयर"), "bi-briefcase"),
    (("tech", "gadget", "टेक", "तकनीक"), "bi-cpu"),
    (("health", "swasthya", "स्वास्थ्य", "सेहत"), "bi-heart-pulse"),
    (("education", "shiksha", "शिक्षा", "एजुकेशन"), "bi-mortarboard"),
    (("job", "career", "naukri", "नौकरी", "करियर"), "bi-person-workspace"),
    (("crime", "apradh", "क्राइम", "अपराध"), "bi-shield-exclamation"),
    (("world", "international", "vishwa", "विश्व", "दुनिया", "अंतरराष्ट्रीय"), "bi-globe2"),
    (("religion", "dharma", "astrology", "धर्म", "ज्योतिष", "आध्यात्म"), "bi-flower1"),
    (("auto", "vehicle", "ऑटो", "गाड़ी"), "bi-car-front"),
    (("lifestyle", "लाइफस्टाइल", "फैशन"), "bi-stars"),
    (("national", "rashtriya", "राष्ट्रीय", "देश"), "bi-flag"),
    (("state", "rajya", "राज्य", "स्थानीय", "शहर"), "bi-geo-alt"),
]


@register.filter
def category_icon(category):
    """Bootstrap icon class for a category.

    Prefers the editor-supplied Category.icon; otherwise infers one from the
    name/slug so the homepage grid never renders a category without an icon.
    """
    if not category:
        return "bi-newspaper"
    explicit = (getattr(category, "icon", "") or "").strip()
    if explicit:
        return explicit if explicit.startswith("bi-") else f"bi-{explicit}"
    haystack = " ".join(
        str(value).lower()
        for value in (getattr(category, "slug", ""), getattr(category, "name", ""), getattr(category, "hindi_name", ""))
        if value
    ) or str(category).lower()
    for keywords, icon in CATEGORY_ICON_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return icon
    return "bi-newspaper"


@register.filter
def category_color(category):
    if not category:
        return FALLBACK_PALETTE[0]
    haystack = " ".join(
        str(value).lower()
        for value in (getattr(category, "slug", ""), getattr(category, "name", ""), getattr(category, "hindi_name", ""))
        if value
    ) or str(category).lower()
    for keywords, color in CATEGORY_COLOR_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return color
    return FALLBACK_PALETTE[hash(haystack) % len(FALLBACK_PALETTE)]
