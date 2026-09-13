"""Whole-site smoke tests.

Two classes of bug motivated these:

* Five templates were deleted while their views still rendered them, and the
  breakage was invisible until a request hit each page.
* Multi-line ``{# ... #}`` template comments render as visible page text,
  because Django's ``{# #}`` is single-line only. That leaked developer notes
  onto live pages.

Both are cheap to catch by rendering every public route and inspecting the HTML.
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from galleries.models import Gallery
from liveblog.models import LiveBlog
from news.models import Article, Category
from videos.models import Video
from webstories.models import WebStory

PUBLIC_ROUTES = [
    "home",
    "news:latest",
    "news:trending",
    "news:search",
    "galleries:list",
    "videos:list",
    "videos:shorts",
    "webstories:list",
    "liveblog:list",
    "core:contact",
    "core:about",
    "core:privacy",
    "core:terms",
    "core:disclaimer",
    "core:editorial_policy",
    "core:grievance",
    "core:advertise",
    "accounts:login",
    "accounts:signup",
    "accounts:forgot_password",
    "robots_txt",
    "healthz",
]

# Text that must never reach a rendered page.
LEAK_MARKERS = ["{#", "#}", "{% comment %}", "{% endcomment %}", "TODO", "FIXME", "Lorem ipsum"]


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class PublicSiteSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="writer", password="pass")
        cls.category = Category.objects.create(name="National", hindi_name="देश", slug="national")
        cls.article = Article.objects.create(
            title="Smoke test story",
            slug="smoke-test-story",
            summary="Summary",
            body="<p>Body</p>",
            category=cls.category,
            author=cls.user,
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        cls.gallery = Gallery.objects.create(title="Gallery", slug="gallery", active=True)
        cls.video = Video.objects.create(
            title="Video", slug="video", youtube_url="https://www.youtube.com/watch?v=abc123", active=True
        )
        cls.story = WebStory.objects.create(title="Story", slug="story", active=True)
        cls.liveblog = LiveBlog.objects.create(title="Live", slug="live", active=True)

    def test_every_public_route_renders(self):
        for name in PUBLIC_ROUTES:
            with self.subTest(route=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200, f"{name} returned {response.status_code}")

    def test_every_detail_page_renders(self):
        for obj in (self.article, self.gallery, self.video, self.story, self.liveblog):
            with self.subTest(obj=type(obj).__name__):
                response = self.client.get(obj.get_absolute_url())
                self.assertEqual(response.status_code, 200)

    def test_no_template_comment_leaks_into_rendered_html(self):
        pages = [reverse(name) for name in PUBLIC_ROUTES if name != "healthz"]
        pages.append(self.article.get_absolute_url())
        for url in pages:
            with self.subTest(url=url):
                body = self.client.get(url).content.decode()
                for marker in LEAK_MARKERS:
                    self.assertNotIn(marker, body, f"{marker!r} leaked into {url}")

    def test_information_pages_have_distinct_content(self):
        """All seven policy pages once rendered one identical paragraph."""
        bodies = {}
        for name in ["core:about", "core:privacy", "core:terms", "core:disclaimer",
                     "core:editorial_policy", "core:grievance", "core:advertise"]:
            content = self.client.get(reverse(name)).content.decode()
            main = content.split('class="static-content"')[-1]
            bodies[name] = main
            self.assertIn("<h2>", main, f"{name} has no content sections")
        self.assertEqual(len(set(bodies.values())), len(bodies), "policy pages share identical content")

    def test_navigation_has_no_dead_query_string_links(self):
        """The primary nav pointed every link at ?q=<term> on a view that
        ignores that parameter, so all of them landed on the same page."""
        body = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("/latest/?q=", body)

    def test_navigation_links_to_real_category_pages(self):
        body = self.client.get(reverse("home")).content.decode()
        self.assertIn(self.category.get_absolute_url(), body)

    def test_signup_is_reachable_from_login(self):
        """Signup worked but nothing linked to it."""
        body = self.client.get(reverse("accounts:login")).content.decode()
        self.assertIn(reverse("accounts:signup"), body)

    def test_article_structured_data_is_ld_json(self):
        """json_script emits application/json, which crawlers ignore."""
        body = self.client.get(self.article.get_absolute_url()).content.decode()
        self.assertIn('type="application/ld+json"', body)
        self.assertNotIn('type="application/json"', body)

    def test_empty_ad_slots_render_nothing(self):
        """With no Advertisement rows, slots must collapse rather than print
        'Advertisement Space' on a live page."""
        body = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("Advertisement Space", body)
        self.assertNotIn("ad-slot", body)

    def test_no_fabricated_weather(self):
        """A fixed '28°C' presented as live data."""
        body = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("मौसम", body)

    def test_epaper_page_honest_when_no_editions_uploaded(self):
        """With no EPaperEdition rows, the page must say so plainly rather
        than linking to a PDF that doesn't exist."""
        resp = self.client.get(reverse("core:epaper"))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn("अभी उपलब्ध नहीं है", body)
        self.assertNotIn(".pdf", body)

    def test_shorts_page_honest_when_no_short_videos_uploaded(self):
        """No Video has is_short=True in this test data -- the Shorts archive
        must say so honestly instead of silently showing long-form videos or
        fabricated placeholder cards."""
        body = self.client.get(reverse("videos:shorts")).content.decode()
        self.assertIn("empty-state", body)
        self.assertNotIn(self.video.get_absolute_url(), body)

    def test_video_with_no_engagement_shows_real_zero_counts(self):
        """A freshly created video has 0 likes/comments -- the detail page
        must show that real 0, not a fabricated non-zero placeholder count.
        Uses a real, embeddable YouTube id -- cls.video's id is too short to
        embed, so it never reaches the branch that carries like/comment data."""
        video = Video.objects.create(
            title="Engagement check", slug="engagement-check",
            youtube_url="https://youtu.be/dQw4w9WgXcQ", active=True,
        )
        body = self.client.get(video.get_absolute_url()).content.decode()
        self.assertIn('"likes": 0', body)
        self.assertIn('"comment_count": 0', body)
