from django import template

register = template.Library()

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
