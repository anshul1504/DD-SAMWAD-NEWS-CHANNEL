from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from news.models import Article, Category

from .models import StorySlide, WebStory


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class PublicWebStoryTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="National", hindi_name="देश", slug="national", active=True,
        )

    def story(self, slug, *, published_at=None, slides=1, active=True, category=None):
        story = WebStory.objects.create(
            title=slug.replace("-", " ").title(),
            slug=slug,
            category=category or self.category,
            published_at=published_at or timezone.now(),
            active=active,
        )
        for index in range(slides):
            StorySlide.objects.create(story=story, heading=f"Slide {index + 1}", order=index)
        return story

    def test_future_and_empty_stories_are_hidden_from_public_listing_and_detail(self):
        visible = self.story("visible")
        future = self.story("future", published_at=timezone.now() + timedelta(hours=2))
        empty = self.story("empty", slides=0)

        response = self.client.get(reverse("webstories:list"))

        self.assertContains(response, visible.title)
        self.assertNotContains(response, future.title)
        self.assertNotContains(response, empty.title)
        self.assertEqual(self.client.get(future.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(empty.get_absolute_url()).status_code, 404)

    def test_unicode_database_slug_has_clean_url_and_old_link_redirects(self):
        story = self.story("हिंदी-कहानी")

        self.assertEqual(story.get_absolute_url(), f"/web-stories/{story.pk}/national-story/")
        self.assertTrue(story.get_absolute_url().isascii())
        legacy = self.client.get(reverse("webstories:legacy_detail", args=[story.slug]))
        self.assertRedirects(legacy, story.get_absolute_url(), status_code=301, fetch_redirect_response=False)
        wrong = self.client.get(reverse("webstories:detail", args=[story.pk, "wrong-label"]))
        self.assertRedirects(wrong, story.get_absolute_url(), status_code=301, fetch_redirect_response=False)

    def test_filtered_story_count_matches_visible_category_results(self):
        other = Category.objects.create(name="Sports", hindi_name="खेल", slug="sports", active=True)
        self.story("national-story")
        self.story("sports-story", category=other)

        response = self.client.get(reverse("webstories:list"), {"category": other.slug})

        self.assertEqual(response.context["total_count"], 1)
        self.assertContains(response, "Sports Story")
        self.assertNotContains(response, "National Story")

    def test_old_story_lane_is_labelled_top_stories_not_24_hours(self):
        old = self.story("older-story", published_at=timezone.now() - timedelta(days=3))

        response = self.client.get(reverse("home"))

        self.assertContains(response, old.title)
        self.assertContains(response, "प्रमुख वेब स्टोरीज")
        self.assertNotContains(response, "आज की तेज झलकियां")

    def test_highlights_fall_back_to_latest_articles_when_flags_are_missing(self):
        author = User.objects.create_user(username="writer")
        article = Article.objects.create(
            title="Latest unflagged article",
            slug="latest-unflagged-article",
            body="<p>Body</p>",
            category=self.category,
            author=author,
            status=Article.Status.PUBLISHED,
            is_top_story=False,
            is_editor_pick=False,
        )

        response = self.client.get(reverse("home"))

        self.assertIn(article, response.context["top_stories"])
        self.assertIn(article, response.context["editor_picks"])

    @override_settings(SITE_URL="https://ddsamvad.com")
    def test_legacy_article_cta_is_saved_as_clean_canonical_url(self):
        author = User.objects.create_user(username="cta-writer")
        article = Article.objects.create(
            title="CTA article",
            slug="हिंदी-लेख",
            body="<p>Body</p>",
            category=self.category,
            author=author,
            status=Article.Status.PUBLISHED,
        )
        story = self.story("cta-story", slides=0)

        slide = StorySlide.objects.create(
            story=story,
            heading="Read article",
            cta_url="https://ddsamvad.com/news/%E0%A4%B9%E0%A4%BF%E0%A4%82%E0%A4%A6%E0%A5%80-%E0%A4%B2%E0%A5%87%E0%A4%96/",
        )

        self.assertEqual(slide.cta_url, f"https://ddsamvad.com{article.get_absolute_url()}")

# Create your tests here.
