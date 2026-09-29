from core.models import EPaperEdition, SiteSettings
from news.models import Article

titles = [
    "फरार CSP नेहा पच्चीसिया को हाईकोर्ट से मिलेगी राहत या जाना होगा जेल? फैसला सुरक्षित",
    "साइबर ठगी से सावधान: WhatsApp पर बैंक खाते से पैसे कटने का फर्जी अलर्ट भेजकर ठगी की कोशिश",
    "280 करोड़ की बंपर कमाई वाली 'हनुमान अंश' में भोपाल का डंका: 8 साल के सात्विक ने 'शुभंकर' बन लूटी महफिल",
]

edition = EPaperEdition.objects.get(edition_date="2026-09-21", city=None)
print("EPAPER", edition.pk, edition.page_count, edition.pages.count(), edition.pdf.url, edition.cover_image.url)
for article in Article.objects.filter(title__in=titles).order_by("pk"):
    print("ARTICLE", article.pk, article.status, article.views, "breaking", article.is_breaking, "top", article.is_top_story, "hero", article.is_homepage_hero, article.get_absolute_url(), article.featured_image.url if article.featured_image else "TEXT_ONLY")
settings = SiteSettings.load()
print("IDENTITY", settings.email, settings.instagram_url, settings.facebook_url, settings.twitter_url, settings.youtube_url)
