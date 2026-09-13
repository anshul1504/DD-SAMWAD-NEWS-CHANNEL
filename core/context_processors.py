import json
from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.core.cache import cache
from django.db.models import Q

from advertisements.models import Advertisement
from liveblog.models import LiveBlog
from locations.models import City
from news.models import Article, Category

from .models import SiteSettings

_JSONLD_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026"}


def _site_url(path="/"):
    base = settings.SITE_URL.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def _canonical_url(request):
    path = request.path
    query = request.GET.urlencode()
    if query:
        path = f"{path}?{query}"
    return _site_url(path)


def _jsonld(data):
    return mark_safe(json.dumps(data, ensure_ascii=False).translate(_JSONLD_ESCAPES))


def global_site_context(request):
    now = timezone.now()
    site_settings = cache.get_or_set("dds:site_settings", SiteSettings.load, 300)
    menu_categories = cache.get_or_set(
        "dds:menu_categories",
        lambda: list(Category.objects.filter(active=True, show_in_menu=True).exclude(slug="home")[:16]),
        300,
    )
    popular_cities = cache.get_or_set(
        "dds:popular_cities",
        lambda: list(City.objects.filter(active=True).select_related("district__state")[:10]),
        600,
    )
    breaking_articles = cache.get_or_set(
        "dds:breaking_articles",
        lambda: list(Article.objects.optimized().breaking()[:8]),
        60,
    )
    active_ads = cache.get_or_set(
        "dds:active_ads",
        lambda: list(
            Advertisement.objects.filter(active=True)
            .filter(Q(start_date__isnull=True) | Q(start_date__lte=now))
        ),
        60,
    )
    active_ads = [ad for ad in active_ads if (not ad.end_date or ad.end_date >= now)]
    # The header's "live update" pill needs somewhere real to point: the live
    # blog actually in progress right now, not a duplicate of "Latest News".
    active_live_blog = cache.get_or_set(
        "dds:active_live_blog",
        lambda: LiveBlog.objects.filter(active=True, status=LiveBlog.Status.LIVE).first(),
        30,
    )
    site_name = site_settings.site_name or "Desh Darpan Samvad"
    logo_url = _site_url("/static/images/dds-final-logo.png")
    organization = {
        "@context": "https://schema.org",
        "@type": "NewsMediaOrganization",
        "@id": _site_url("/#organization"),
        "name": site_name,
        "url": _site_url("/"),
        "logo": {
            "@type": "ImageObject",
            "url": logo_url,
        },
        "email": site_settings.email or settings.DEFAULT_FROM_EMAIL,
    }
    same_as = [
        url for url in [
            site_settings.facebook_url,
            site_settings.instagram_url,
            site_settings.youtube_url,
            site_settings.twitter_url,
            site_settings.telegram_url,
            site_settings.whatsapp_url,
        ] if url
    ]
    if same_as:
        organization["sameAs"] = same_as
    if site_settings.primary_phone:
        organization["telephone"] = site_settings.primary_phone
    if site_settings.address:
        organization["address"] = site_settings.address

    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": _site_url("/#website"),
        "name": site_name,
        "url": _site_url("/"),
        "publisher": {"@id": _site_url("/#organization")},
        "potentialAction": {
            "@type": "SearchAction",
            "target": _site_url(reverse("news:search")) + "?q={search_term_string}",
            "query-input": "required name=search_term_string",
        },
    }
    return {
        "site_settings": site_settings,
        "menu_categories": menu_categories,
        "breaking_articles": breaking_articles,
        "popular_cities": popular_cities,
        "active_ads": active_ads,
        "active_live_blog": active_live_blog,
        "today": now,
        "site_url": settings.SITE_URL.rstrip("/"),
        "canonical_url": _canonical_url(request),
        "default_og_image": logo_url,
        "organization_jsonld": _jsonld(organization),
        "website_jsonld": _jsonld(website),
    }
