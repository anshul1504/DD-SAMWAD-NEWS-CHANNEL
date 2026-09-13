from django.utils import timezone
from django.core.cache import cache
from django.db.models import Q

from advertisements.models import Advertisement
from liveblog.models import LiveBlog
from locations.models import City
from news.models import Article, Category

from .models import SiteSettings


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
    return {
        "site_settings": site_settings,
        "menu_categories": menu_categories,
        "breaking_articles": breaking_articles,
        "popular_cities": popular_cities,
        "active_ads": active_ads,
        "active_live_blog": active_live_blog,
        "today": now,
    }
