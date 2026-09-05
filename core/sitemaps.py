from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from galleries.models import Gallery
from news.models import Article, Category
from videos.models import Video
from webstories.models import WebStory


class ArticleSitemap(Sitemap):
    changefreq = "hourly"
    priority = 0.9

    def items(self):
        return Article.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Category.objects.filter(active=True)


class GallerySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.6

    def items(self):
        return Gallery.objects.filter(active=True)


class VideoSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.6

    def items(self):
        return Video.objects.filter(active=True)


class WebStorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.6

    def items(self):
        return WebStory.objects.filter(active=True)


class StaticSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return ["home", "news:latest", "news:trending", "galleries:list", "videos:list", "webstories:list", "liveblog:list", "core:about", "core:contact"]

    def location(self, item):
        return reverse(item)
