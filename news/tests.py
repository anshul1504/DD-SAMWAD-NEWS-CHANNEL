from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Article, Category


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class PublicNewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="writer", password="pass")
        self.category = Category.objects.create(name="National", hindi_name="देश", slug="national")
        self.article = Article.objects.create(
            title="Published story",
            slug="published-story",
            summary="Summary",
            body="<p>Body text for a published story.</p>",
            category=self.category,
            author=self.user,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
            is_breaking=True,
        )
        self.draft = Article.objects.create(
            title="Draft story",
            slug="draft-story",
            body="Draft",
            category=self.category,
            author=self.user,
            status=Article.Status.DRAFT,
        )

    def test_homepage_loads_and_hides_drafts(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published story")
        self.assertNotContains(response, "Draft story")

    def test_article_detail_increments_view_once_per_session(self):
        url = self.article.get_absolute_url()
        self.client.get(url)
        self.client.get(url)
        self.article.refresh_from_db()
        self.assertEqual(self.article.views, 1)

    def test_draft_article_is_not_public(self):
        response = self.client.get(self.draft.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_category_and_search_pages_load(self):
        self.assertEqual(self.client.get(self.category.get_absolute_url()).status_code, 200)
        response = self.client.get(reverse("news:search"), {"q": "Published"})
        self.assertContains(response, "Published story")

# Create your tests here.
