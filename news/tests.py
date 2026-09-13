from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Article, Bookmark, Category


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


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class SearchMitigationTests(TestCase):
    """Search chained icontains across eight fields including `body`, which is a
    full table scan of every article's HTML on an unauthenticated endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(username="writer", password="pass")
        self.category = Category.objects.create(name="National", hindi_name="देश", slug="national")
        self.article = Article.objects.create(
            title="Monsoon report",
            slug="monsoon-report",
            summary="Rainfall summary",
            body="<p>A very distinctive phrase appears only in the body text.</p>",
            category=self.category,
            author=self.user,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def test_empty_search_returns_no_results(self):
        response = self.client.get(reverse("news:search"), {"q": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 0)
        self.assertFalse(response.context["query_too_short"])

    def test_one_character_search_is_rejected(self):
        response = self.client.get(reverse("news:search"), {"q": "a"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["query_too_short"])
        self.assertEqual(response.context["result_count"], 0)

    def test_two_character_search_is_rejected(self):
        response = self.client.get(reverse("news:search"), {"q": "mo"})
        self.assertTrue(response.context["query_too_short"])
        self.assertEqual(response.context["result_count"], 0)

    def test_three_character_search_is_accepted(self):
        response = self.client.get(reverse("news:search"), {"q": "Mon"})
        self.assertFalse(response.context["query_too_short"])
        self.assertContains(response, "Monsoon report")

    def test_body_text_is_no_longer_searched(self):
        # The phrase exists only in `body`. Matching it would mean the expensive
        # unindexed scan is back.
        response = self.client.get(reverse("news:search"), {"q": "distinctive phrase"})
        self.assertEqual(response.context["result_count"], 0)

    def test_title_summary_and_keyword_search_still_work(self):
        self.assertEqual(
            self.client.get(reverse("news:search"), {"q": "Monsoon"}).context["result_count"], 1
        )
        self.assertEqual(
            self.client.get(reverse("news:search"), {"q": "Rainfall"}).context["result_count"], 1
        )

    def test_result_count_matches_paginator_count(self):
        # result_count must come from the paginator, not a second full query.
        response = self.client.get(reverse("news:search"), {"q": "Monsoon"})
        self.assertEqual(response.context["result_count"], response.context["page_obj"].paginator.count)

    def test_malicious_input_is_handled_safely(self):
        for payload in ["'; DROP TABLE news_article; --", "<script>alert(1)</script>", "%%%", "\x00abc"]:
            response = self.client.get(reverse("news:search"), {"q": payload})
            self.assertEqual(response.status_code, 200)
        self.assertTrue(Article.objects.filter(pk=self.article.pk).exists())

    def test_search_pagination_works(self):
        for index in range(25):
            Article.objects.create(
                title=f"Monsoon extra {index}",
                slug=f"monsoon-extra-{index}",
                body="<p>Body</p>",
                category=self.category,
                author=self.user,
                status=Article.Status.PUBLISHED,
                published_at=timezone.now(),
            )
        first = self.client.get(reverse("news:search"), {"q": "Monsoon"})
        self.assertEqual(first.context["result_count"], 26)
        self.assertTrue(first.context["page_obj"].has_next())

        second = self.client.get(reverse("news:search"), {"q": "Monsoon", "page": 2})
        self.assertEqual(second.context["page_obj"].number, 2)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class BookmarkMethodTests(TestCase):
    """Bookmarking mutated state on GET, so any page could force a logged-in
    user to bookmark articles, and prefetching crawlers triggered it."""

    def setUp(self):
        self.user = User.objects.create_user(username="reader", password="pass")
        self.category = Category.objects.create(name="National", hindi_name="देश", slug="national")
        self.article = Article.objects.create(
            title="Saveable story",
            slug="saveable-story",
            body="<p>Body</p>",
            category=self.category,
            author=self.user,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        self.client.force_login(self.user)

    def test_get_does_not_create_bookmark(self):
        response = self.client.get(reverse("news:bookmark", args=[self.article.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_post_creates_bookmark(self):
        response = self.client.post(reverse("news:bookmark", args=[self.article.pk]))
        self.assertRedirects(response, self.article.get_absolute_url())
        self.assertTrue(Bookmark.objects.filter(user=self.user, article=self.article).exists())

    def test_post_is_idempotent(self):
        self.client.post(reverse("news:bookmark", args=[self.article.pk]))
        self.client.post(reverse("news:bookmark", args=[self.article.pk]))
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_bookmark_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("news:bookmark", args=[self.article.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_csrf_is_enforced_on_bookmark_post(self):
        enforcing = Client(enforce_csrf_checks=True)
        enforcing.force_login(self.user)
        response = enforcing.post(reverse("news:bookmark", args=[self.article.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Bookmark.objects.count(), 0)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ArticleShareMetadataTests(TestCase):
    """Every share showed the site logo instead of the story image."""

    def setUp(self):
        self.user = User.objects.create_user(username="writer", password="pass")
        self.category = Category.objects.create(name="National", hindi_name="देश", slug="national")
        self.article = Article.objects.create(
            title="Shareable story",
            slug="shareable-story",
            body="<p>Body</p>",
            category=self.category,
            author=self.user,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def test_article_page_declares_article_og_type(self):
        response = self.client.get(self.article.get_absolute_url())
        self.assertContains(response, '<meta property="og:type" content="article">', html=False)

    def test_non_article_page_keeps_website_og_type(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<meta property="og:type" content="website">', html=False)

    def test_og_image_falls_back_to_absolute_logo_url(self):
        # No featured image on this article, so the logo is used — but it must
        # still be an absolute URL, which Open Graph requires.
        response = self.client.get(self.article.get_absolute_url())
        content = response.content.decode()
        self.assertIn('property="og:image" content="http://testserver/static/images/dds-final-logo.png"', content)

    def test_og_image_uses_featured_image_when_present(self):
        self.article.featured_image = "articles/2026/09/story.jpg"
        self.article.save(update_fields=["featured_image"])
        response = self.client.get(self.article.get_absolute_url())
        content = response.content.decode()
        self.assertIn("articles/2026/09/story.jpg", content)
        self.assertIn('property="og:image" content="http://testserver/media/', content)
