from datetime import timedelta
import xml.etree.ElementTree as ET

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from news.models import Article, Category


@override_settings(
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    SITE_URL="https://ddsamvad.com",
)
class NewsSitemapTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="news-writer")
        self.category = Category.objects.create(name="National", hindi_name="देश", slug="national")

    def article(self, slug, published_at, status=Article.Status.PUBLISHED, image=""):
        return Article.objects.create(
            title=f"समाचार {slug}",
            slug=slug,
            body="<p>समाचार सामग्री</p>",
            category=self.category,
            author=self.author,
            status=status,
            published_at=published_at,
            featured_image=image,
        )

    def test_recent_published_articles_appear_with_news_and_image_metadata(self):
        article = self.article(
            "recent-news",
            timezone.now() - timedelta(hours=1),
            image="articles/2026/10/recent.jpg",
        )

        response = self.client.get(reverse("news_sitemap"))
        body = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        self.assertIn(f"https://ddsamvad.com{article.get_absolute_url()}", body)
        self.assertIn("<news:language>hi</news:language>", body)
        self.assertIn(f"<news:title>{article.title}</news:title>", body)
        self.assertIn("https://ddsamvad.com/media/articles/2026/10/recent.jpg", body)
        ET.fromstring(response.content)

    def test_old_draft_and_future_articles_are_excluded(self):
        recent = self.article("included", timezone.now() - timedelta(hours=2))
        old = self.article("too-old", timezone.now() - timedelta(days=3))
        draft = self.article("draft", timezone.now(), status=Article.Status.DRAFT)
        future = self.article("future", timezone.now() + timedelta(hours=2))

        body = self.client.get(reverse("news_sitemap")).content.decode()

        self.assertIn(recent.get_absolute_url(), body)
        for article in (old, draft, future):
            self.assertNotIn(article.get_absolute_url(), body)

    def test_robots_advertises_general_and_news_sitemaps(self):
        body = self.client.get(reverse("robots_txt")).content.decode()

        self.assertIn("Sitemap: https://ddsamvad.com/sitemap.xml", body)
        self.assertIn("Sitemap: https://ddsamvad.com/news-sitemap.xml", body)

    def test_general_sitemap_does_not_publish_redirecting_shorts_entry(self):
        body = self.client.get(reverse("django.contrib.sitemaps.views.sitemap")).content.decode()

        self.assertNotIn("https://ddsamvad.com/shorts/", body)

    def test_canonical_ignores_tracking_query_parameters(self):
        response = self.client.get("/?utm_source=campaign")

        self.assertEqual(response.context["canonical_url"], "https://ddsamvad.com/")
